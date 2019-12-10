# -*- coding: utf-8 -*-

from __builtin__ import False
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.of_planning_tournee.wizard.rdv import ROUTING_BASE_URL, ROUTING_VERSION, ROUTING_PROFILE
from odoo.addons.of_utils.models.of_utils import se_chevauchent, float_2_heures_minutes, heures_minutes_2_float
import urllib
import requests
import re
import pytz

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from odoo.tools.float_utils import float_compare


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

class HREmployee(models.Model):
    _inherit = "hr.employee"

    of_tache_ids = fields.Many2many('of.planning.tache', 'of_employee_tache_rel', 'employee_id', 'tache_id', u'Tâches')
    of_toutes_taches = fields.Boolean(string=u'Apte à toutes les taches')
    of_equipe_ids = fields.Many2many('of.planning.equipe', 'of_planning_employee_rel', 'employee_id', 'equipe_id', u'Équipes')
    of_changed_intervention_id = fields.Many2one('of.planning.intervention', string=u"Dernière intervention modifiée")  # api.depends dans of.planning.intervention
    of_est_intervenant = fields.Boolean(string=u"Est intervenant ?", default=False)

    @api.multi
    def peut_faire(self, tache_id, all_required=False):
        if all_required:
            return len(self.filtered(lambda e: (tache_id not in e.of_tache_ids) and not e.of_toutes_taches)) == 0
        return len(self.filtered(lambda e: (tache_id in e.of_tache_ids) or e.of_toutes_taches))

    @api.multi
    def get_taches_possibles(self, en_commun=False):
        self = self.filtered(lambda e: not e.of_toutes_taches)
        if not self:
            return self.env['of.planning.tache'].search([])
        taches = self.mapped('of_tache_ids')
        if not en_commun:
            return taches
        for employee in self:
            taches = taches.filtered(lambda t: t.id in employee.of_tache_ids.ids)
        return taches


class OfPlanningTacheCateg(models.Model):
    _name = "of.planning.tache.categ"
    _description = u"Planning OpenFire : Catégories de tâches"

    name = fields.Char(u'Libellé', size=64, required=True)
    description = fields.Text('Description')
    tache_ids = fields.One2many('of.planning.tache', 'tache_categ_id', string=u"Tâches")
    active = fields.Boolean('Actif', default=True)
    sequence = fields.Integer(u'Séquence', help=u"Ordre d'affichage (plus petit en premier)")


class OfPlanningTache(models.Model):
    _name = "of.planning.tache"
    _description = u"Planning OpenFire : Tâches"

    @api.model
    def _get_employee_ids_domain(self):
        return [('of_est_intervenant', '=', True)]

    name = fields.Char(u'Libellé', size=64, required=True)
    description = fields.Text('Description')
    verr = fields.Boolean(u'Verrouillé')
    product_id = fields.Many2one('product.product', 'Produit')
    active = fields.Boolean('Actif', default=True)
    imp_detail = fields.Boolean(u'Imprimer Détail', help=u"""Impression du détail des tâches dans le planning semaine
Si cette option n'est pas cochée, seule la tâche la plus souvent effectuée dans la journée apparaîtra""", default=True)
    duree = fields.Float(u'Durée par défaut', digits=(12, 5), default=1.0)
    tache_categ_id = fields.Many2one('of.planning.tache.categ', string=u"Catégorie de tâche")
    is_crm = fields.Boolean(u'Tâche CRM')
    equipe_ids = fields.Many2many('of.planning.equipe', 'equipe_tache_rel', 'tache_id', 'equipe_id', u'Équipes qualifiées')
    #employee_ids = fields.Many2many('hr.employee', 'of_employee_tache_rel', 'tache_id', 'employee_id', u'Employés qualifiés',
    #                                domain=_get_employee_ids_domain)
    employee_ids = fields.Many2many('hr.employee', u'Employés qualifiés', compute="_compute_employee_ids")
    category_id = fields.Many2one('hr.employee.category', string=u"Catégorie d'employés")
    #employee_nb = fields.Integer(string=u'Nombre d\'intervenants', default=1)

    @api.multi
    def _compute_employee_ids(self):
        intervenants = self.env['hr.employee'].search([('of_est_intervenant', '=', True)])
        for tache in self:
            tache.employee_ids = intervenants.filtered(lambda i: i.of_toutes_taches or tache.id in i.of_tache_ids.ids)

    @api.multi
    def unlink(self):
        if self.search([('id', 'in', self._ids), ('verr', '=', True)]):
            raise ValidationError(u'Vous essayez de supprimer une tâche verrouillée.')
        return super(OfPlanningTache, self).unlink()

class OfPlanningEquipe(models.Model):
    _name = "of.planning.equipe"
    _description = u"Équipe d'intervention"
    _order = "sequence, name"

    @api.model
    def _get_employee_ids_domain(self):
        return [('of_est_intervenant', '=', True)]

    @api.multi
    def check_no_overlapping(self):
        for equipe in self:
            for i in range(1, 8):
                creneaux_du_jour = equipe.of_creneau_ids.filtered(lambda jour: jour.jour_number == i)
                la_len = len(creneaux_du_jour)
                for j in range(la_len):
                    for k in range(j+1, la_len):
                        d1 = creneaux_du_jour[j].heure_debut
                        f1 = creneaux_du_jour[j].heure_fin
                        d2 = creneaux_du_jour[k].heure_debut
                        f2 = creneaux_du_jour[k].heure_fin
                        if se_chevauchent(d1, f1, d2, f2):
                            #raise UserError(u"Oups! Des créneaux se chevauchent")
                            return False
                creneaux_temp_du_jour = equipe.of_creneau_temp_ids.filtered(lambda jour: jour.jour_number == i)
                la_len = len(creneaux_temp_du_jour)
                for j in range(la_len):
                    for k in range(j+1, la_len):
                        d1 = creneaux_temp_du_jour[j].heure_debut
                        f1 = creneaux_temp_du_jour[j].heure_fin
                        d2 = creneaux_temp_du_jour[k].heure_debut
                        f2 = creneaux_temp_du_jour[k].heure_fin
                        if se_chevauchent(d1, f1, d2, f2):
                            #raise UserError(u"Oups! Des créneaux se chevauchent")
                            return False
        return True

    def _default_tz(self):
        return self.env.user.tz or 'Europe/Paris'

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    name = fields.Char(u'Équipe', size=128, required=True)
    note = fields.Text('Description')
    employee_ids = fields.Many2many('hr.employee', 'of_planning_employee_rel', 'equipe_id', 'employee_id', u'Employés',
                                    domain=_get_employee_ids_domain)
    active = fields.Boolean('Actif', default=True)
    category_ids = fields.Many2many(
        'hr.employee.category', 'equipe_category_rel', 'equipe_id', 'category_id', string=u'Catégories')
    intervention_ids = fields.One2many('of.planning.intervention', 'equipe_id', u'Interventions liées', copy=False)
    tache_ids = fields.Many2many('of.planning.tache', 'equipe_tache_rel', 'equipe_id', 'tache_id', u'Compétences')
    hor_md = fields.Float(u'Matin début', digits=(12, 5))
    hor_mf = fields.Float('Matin fin', digits=(12, 5))
    hor_ad = fields.Float(u'Après-midi début', digits=(12, 5))
    hor_af = fields.Float(u'Après-midi fin', digits=(12, 5))
    jour_ids = fields.Many2many(
        'of.jours', 'of_equipe_jours_rel', 'equipe_id', 'jour_id', string='Jours', default=_get_default_jours)
    sequence = fields.Integer(u'Séquence', help=u"Ordre d'affichage (plus petit en premier)")
    color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D")
    color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0")
    tz = fields.Selection(
        _tz_get, string='Fuseau horaire', required=True, default=lambda self: self._default_tz(),
        help=u"Le fuseau horaire de l'équipe d'intervention")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)

    # Ajout des horaires avancés
    mode_horaires = fields.Selection([
        ("easy", "Facile"),
        ("advanced", u"Avancé")], string=u"Mode de sélection des horaires", required=True, default="easy")
    modele_id = fields.Many2one("of.horaire.modele", string=u"Modèle")
    of_creneau_ids = fields.Many2many(
        'of.horaire.creneau', 'of_equipe_creneau_rel', 'equipe_id', 'creneau_id', string=u"Créneaux",
        order="jour_number, heure_debut")
    of_creneau_temp_ids = fields.Many2many(
        'of.horaire.creneau', 'of_equipe_creneau_temp_rel', 'equipe_id', 'creneau_id', string=u"Créneaux",
        order="jour_number, heure_debut")
    of_creneau_temp_start = fields.Date(string=u"Début des horaires temporaires")
    of_creneau_temp_stop = fields.Date(string="Fin des horaires temporaires")

    _sql_constraints = [
        ('of_creneau_temp_start_stop_constraint', 'CHECK ( of_creneau_temp_start <= of_creneau_temp_stop )', _(u"La date de début de validité doit être antérieure ou égale à celle de fin")),
    ]

    _constraints = [
        (check_no_overlapping, u'Vous ne pourrez pas sauvegarder tant que des créneaux se chevauchent.', []),
    ]

    @api.onchange("of_creneau_ids", "of_creneau_temp_ids")
    def _onchange_creneaux(self):
        if not self.check_no_overlapping():
            raise UserError(u"Oups ! Des créneaux se chevauchent. Veuillez vous assurer que ce ne soit plus le cas avant de sauvegarder.")

    @api.depends('tz')
    def _compute_tz_offset(self):
        for equipe in self:
            equipe.tz_offset = datetime.now(pytz.timezone(equipe.tz or 'GMT')).strftime('%z')

class OfPlanningInterventionRaison(models.Model):
    _name = "of.planning.intervention.raison"
    _description = u"Raisons d'intervention reportée"

    name = fields.Char(u'Libellé', size=128, required=True)


class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _description = "Planning d'intervention OpenFire"
    _inherit = ["of.readgroup", "of.calendar.mixin", 'mail.thread']
    _order = 'date'

    @api.multi
    def check_coherence_dates(self):
        for intervention in self:
            if intervention.date_deadline_forcee and intervention.forcer_dates and intervention.date and intervention.duree:
                diff_heures = relativedelta(fields.Datetime.from_string(intervention.date_deadline_forcee),
                                            fields.Datetime.from_string(intervention.date))
                # on convertit la durée pour faciliter la comparaison
                heures, minutes = float_2_heures_minutes(intervention.duree)
                duree_rd = relativedelta(hours=heures, minutes=minutes)
                if diff_heures < duree_rd and (duree_rd - diff_heures).minutes > 1:
                    return False
        return True

    _sql_constraints = [
        ('dates_forcees_constraint', 'CHECK ( date <= date_deadline_forcee )', _(u"La date de début doit être antérieure ou égale à celle de fin")),
    ]

    _constraints = [
        (check_coherence_dates, u"Attention /!\ la date de fin doit être au moins égale à la date de début + la durée", []),
    ]

    @api.model
    def _get_employee_ids_domain(self):
        return [('of_est_intervenant', '=', True)]

    @api.depends('tz')
    def _compute_tz_offset(self):
        for intervention in self:
            intervention.tz_offset = datetime.now(pytz.timezone(intervention.employee_ids and intervention.employee_ids[0].tz or 'GMT')).strftime('%z')

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    name = fields.Char(string=u'Libellé', required=True)
    date = fields.Datetime(string='Date intervention', required=True, track_visibility='always')
    date_deadline = fields.Datetime(compute="_compute_date_deadline", string='Date fin', store=True, track_visibility='always')
    forcer_dates = fields.Boolean("Forcer les dates", default=False, help=u"/!\\")
    date_deadline_forcee = fields.Datetime(string=u"Date fin (forcée)")
    duree = fields.Float(string=u'Durée intervention', required=True, digits=(12, 5), track_visibility='always')
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.uid)
    partner_id = fields.Many2one('res.partner', string='Client', compute='_compute_partner_id', store=True)
    address_id = fields.Many2one('res.partner', string='Adresse', track_visibility='onchange')
    address_city = fields.Char(related='address_id.city', string="Ville", oldname="partner_city")
    address_zip = fields.Char(related='address_id.zip')
    secteur_id = fields.Many2one(related='address_id.of_secteur_tech_id', readonly=True)
    raison_id = fields.Many2one('of.planning.intervention.raison', string='Raison')
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche", required=True)
    tache_categ_id = fields.Many2one(related="tache_id.tache_categ_id", readonly=True)
    tache_name = fields.Char(related='tache_id.name')
    equipe_id = fields.Many2one('of.planning.equipe', string=u'Équipe', oldname='poseur_id')
    employee_ids = fields.Many2many('hr.employee', 'of_employee_intervention_rel', 'intervention_id', 'employee_id',
                                    string='Intervenants', required=True, domain=_get_employee_ids_domain)
    employee_main_id = fields.Many2one('hr.employee', string=u"Employé principal", compute="_compute_employee_main_id", store=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', u'Confirmé'),
        ('done', u'Réalisé'),
        ('unfinished', u'Inachevé'),
        ('cancel', u'Annulé'),
        ('postponed', u'Reporté'),
        ], string=u'État', index=True, readonly=True, default='draft')
    company_id = fields.Many2one('res.company', string='Magasin', required=True, default=lambda self: self.env.user.company_id.id)
    tag_ids = fields.Many2many('of.planning.tag', column1='intervention_id', column2='tag_id', string=u'Étiquettes')
    description = fields.Html(string='Description')  # Non utilisé, changé pour notes intervention
    origin_interface = fields.Char(string=u"Origine création", default=u"Manuelle")

    """mode_horaires = fields.Selection([
        ("easy", "Facile"),
        ("advanced", u"Avancé")], string="Mode de Sélection des horaires", default="easy")
    of_creneau_ids = fields.Many2many("of.horaire.creneau", "of_intervention_creneau_rel", "intervention_id", "creneau_id", string=u"Créneaux", order="jour_number, heure_debut")
    of_creneau_temp_ids = fields.Many2many("of.horaire.creneau", "of_intervention_creneau_temp_rel", "intervention_id", "creneau_id", string=u"Créneaux", order="jour_number, heure_debut")
    of_creneau_temp_start = fields.Date(string=u"Début des horaires temporaires")
    of_creneau_temp_stop = fields.Date(string="Fin des horaires temporaires")
    hor_md = fields.Float(string=u'Matin début', digits=(12, 5))
    hor_mf = fields.Float(string='Matin fin', digits=(12, 5))
    hor_ad = fields.Float(string=u'Après-midi début', digits=(12, 5))
    hor_af = fields.Float(string=u'Après-midi fin', digits=(12, 5))
    jour_ids = fields.Many2many('of.jours', 'of_intervention_jours_rel', 'intervention_id', 'jour_id', string='Jours', default=_get_default_jours)"""
    tz = fields.Selection(_tz_get, compute='_compute_tz', string="fuseau horaires")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)

    """# champs copiés pour le readonly, le xml, les onchange Many2many
    mode_horaires_readonly = fields.Selection(related="mode_horaires", readonly=True, string="Mode de Sélection des horaires")
    of_creneau_readonly_ids = fields.Many2many(related="of_creneau_ids", readonly=True)
    of_creneau_temp_readonly_ids = fields.Many2many(related="of_creneau_temp_ids", readonly=True)
    of_creneau_temp_start_readonly = fields.Date(related="of_creneau_temp_start", readonly=True)
    of_creneau_temp_stop_readonly = fields.Date(related="of_creneau_temp_stop", readonly=True)
    hor_md_readonly = fields.Float(related="hor_md", readonly=True)
    hor_mf_readonly = fields.Float(related="hor_mf", readonly=True)
    hor_ad_readonly = fields.Float(related="hor_ad", readonly=True)
    hor_af_readonly = fields.Float(related="hor_af", readonly=True)
    jour_readonly_ids = fields.Many2many(related="jour_ids", readonly=True)"""

    # 3 champs ajoutés pour la vue map
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')
    precision = fields.Selection(related='address_id.precision')
    partner_name = fields.Char(related='partner_id.name')

    category_id = fields.Many2one(related='tache_id.category_id', string=u"Type de tâche")
    verif_dispo = fields.Boolean(string=u'Vérif chevauchement', help=u"Vérifier que cette intervention n'en chevauche pas une autre", default=True)
    gb_employee_id = fields.Many2one('hr.employee', compute=lambda *a, **k: {}, search='_search_gb_employee_id',
                                     string="Intervenant", of_custom_groupby=True)

    of_color_ft = fields.Char(related="employee_main_id.of_color_ft", readonly=True, oldname='color_ft')
    of_color_bg = fields.Char(related="employee_main_id.of_color_bg", readonly=True, oldname='color_bg')

    order_id = fields.Many2one("sale.order", string=u"Commande associée", domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")
    of_notes_intervention = fields.Html(related='order_id.of_notes_intervention', readonly=True)
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)
    cleantext_description = fields.Text(compute='_compute_cleantext_description')
    cleantext_intervention = fields.Text(compute='_compute_cleantext_intervention', store=True)
    jour = fields.Char("Jour", compute="_compute_jour")
    jour_fin = fields.Char("Jour fin", compute="_compute_jour")
    jour_fin_force = fields.Char(u"Jour fin forcé", compute="_compute_jour")
    date_date = fields.Date(string='Jour intervention', compute='_compute_date_date', search='_search_date_date', readonly=True)

    template_id = fields.Many2one('of.planning.intervention.template', string=u"Modèle d'intervention")
    number = fields.Char(String=u"Numéro", copy=False)
    calendar_name = fields.Char(string="Calendar Name", compute="_compute_calendar_name")
######################## debut de verifier / refaire
    interv_before_id = fields.Many2one('of.planning.intervention', compute="_compute_interventions_before_after", store=True)
    interv_after_id = fields.Many2one('of.planning.intervention', compute="_compute_interventions_before_after", store=True)
    before_to_this = fields.Float(compute="_compute_interval", store=True, digits=(12, 5))

    def compare_date(self, date1, date2, compare="==", isdatetime=False):
        if not date1 or not date2:
            return False
        date1 = fields.Datetime.from_string(date1)
        date2 = fields.Datetime.from_string(date2)
        return safe_eval("date1 " + compare + " date2", {'date1': date1.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date1.strftime("%d/%m/%Y"),
                                                         'date2': date2.strftime("%d/%m/%Y %H:%M:%S") if isdatetime else date2.strftime("%d/%m/%Y")})

    @api.depends('employee_main_id', 'employee_main_id.of_changed_intervention_id')
    def _compute_interventions_before_after(self):
        intervention_obj = self.env['of.planning.intervention']
        for interv in self:
            if interv.compare_date(interv.date, fields.Datetime.now(), compare=">") or not interv.compare_date(interv.date, interv.employee_main_id.of_changed_intervention_id.date):
                continue
            if interv.interv_before_id and interv.interv_before_id == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date) + relativedelta(hour=0, minute=0, second=0))
                interv.interv_before_id = intervention_obj.search([('date_deadline', '<=', interv.date), ('date', '>=', limit_date), ('employee_main_id', '=', interv.employee_main_id.id)], order='date DESC', limit=1)
            if interv.interv_after_id and interv.interv_after_id == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date) + relativedelta(days=1, hour=0, minute=0, second=0))
                interv.interv_after_id = intervention_obj.search([('date', '>=', interv.date_deadline), ('date', '<=', limit_date), ('employee_main_id', '=', interv.employee_main_id.id)], order='date ASC', limit=1)
            if not interv.interv_before_id or interv == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date) + relativedelta(hour=0, minute=0, second=0))
                res = intervention_obj.search([('date_deadline', '<=', interv.date), ('date', '>=', limit_date), ('employee_main_id', '=', interv.employee_main_id.id)], order='date DESC', limit=1)
                if res:
                    interv.interv_before_id = res
            if not interv.interv_after_id or interv == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date) + relativedelta(days=1, hour=0, minute=0, second=0))
                res = intervention_obj.search([('date', '>=', interv.date_deadline), ('date', '<=', limit_date), ('employee_main_id', '=', interv.employee_main_id.id)], order='date ASC', limit=1)
                if res:
                    interv.interv_after_id = res

    @api.depends('interv_before_id')
    def _compute_interval(self):
        for interv in self:
            if not interv.interv_before_id or not interv.interv_before_id.address_id or not interv.address_id:
                continue
            origine = interv.interv_before_id.address_id
            arrivee = interv.address_id
            query = ROUTING_BASE_URL + "route/" + ROUTING_VERSION + "/" + ROUTING_PROFILE + "/"

            # Listes de coordonnées : ATTENTION OSRM prend ses coordonnées sous form (lng, lat)
            coords_str = str(origine.geo_lng) + "," + str(origine.geo_lat)
            coords_str += ";" + str(arrivee.geo_lng) + "," + str(arrivee.geo_lat)

            query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
            full_query = query_send + coords_str + "?"
            try:
                req = requests.get(full_query)
                res = req.json()
            except Exception as e:
                raise UserError(
                    u"Impossible de contacter le serveur de routage. Assurez-vous que votre connexion internet est opérationnelle et que l'URL est définie (%s)." % e)

            if res and res.get('routes'):
                interv.before_to_this = (float(res['routes'].pop(0)['duration']) / 60.0) / 60.0
######################### fin de vérifier / refaire

    @api.multi
    def get_interv_prec_suiv(self, employee_id):
        """renvois l'intervention précédente à celle-ci, pour l'employé donné
        (différent potentiellement de interv_before_id pour les interventions à plusieurs employés)"""
        if not self:
            return (False, False)
        self.ensure_one()
        if not employee_id:
            employee_id = self.employee_ids and self.employee_ids[0].id
        interv_obj = self.env['of.planning.intervention']
        interv_prec = interv_obj.search([
            ('date_date', '=', self.date_date),
            ('date', '<', self.date),  # strict pour ne pas récupérer l'intervention du self
            ('employee_ids', 'in', employee_id)
        ], order="date DESC", limit=1)
        interv_suiv = interv_obj.search([
            ('date_date', '=', self.date_date),
            ('date', '>', self.date),  # strict pour ne pas récupérer l'intervention du self
            ('employee_ids', 'in', employee_id)
        ], order="date DESC", limit=1)
        return (interv_prec or False, interv_suiv or False)

    @api.model_cr_context
    def _auto_init(self):
        # Lors de la 1ère mise à jour après la refonte des équipes (sept. 2019), on migre les données existantes.
        cr = self._cr
        cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'of_employee_intervention_rel'")
        existe_avant = bool(cr.fetchall())
        res = super(OfPlanningIntervention, self)._auto_init()
        cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'of_employee_intervention_rel'")
        existe_apres = bool(cr.fetchall())
        # Si le champ employee_ids n'est pas un many2many avant et l'est après la mise à jour,
        # c'est que l'on est à la 1ère mise à jour après la refonte du planning, on doit faire la migration des données.
        if not existe_avant and existe_apres:
            # On a rendu le champ company_id obligatoire.
            # On peuple ce champ avec la société principale de l'utilisateur de l'intervention quand il n'est pas rempli.
            cr.execute("UPDATE of_planning_intervention "
                "SET company_id = res_users.company_id "
                "FROM res_users "
                "WHERE of_planning_intervention.company_id IS Null")

            # Pour les équipes qui n'ont pas d'employé, on en crée un au nom de l'équipe.
            equipe_obj = self.env['of.planning.equipe']
            employee_obj = self.env['hr.employee']
            for equipe in equipe_obj.search([('employee_ids', '=', False)]):
                employee_obj.create({
                    'name': u"Équipe " + equipe.name,
                    'of_est_intervenant': True,
                    'of_equipe_ids': [(4, equipe.id)]
                })

            # On peuple le champ employee_ids de chaque rdv avec les employés de l'équipe du rdv.
            cr.execute("INSERT INTO of_employee_intervention_rel(intervention_id, employee_id) "
                       "SELECT opi.id, oper.employee_id "
                       "FROM of_planning_intervention opi, of_planning_equipe ope, of_planning_employee_rel oper "
                       "WHERE opi.equipe_id = ope.id "
                       "AND oper.equipe_id = opi.equipe_id")

            # Bascule des couleurs du planning des employés.
            # Règle retenue : prend en priorité la couleur de l'utilisateur lié si il existe, sinon celle de l'équipe.

            # On recopie le choix des couleurs du planning de l'équipe dans les employés.
            # Si un employé est membre de plusieurs équipes, ce sont les couleurs de la dernière équipe renvoyée en SQL qui l'emportent.
            # Et le champ of_est_intervenant dans hr_employee doit être initialisé à vrai pour les employés qui sont dans une équipe.
            # On en profite de le faire avec l'initialisation des couleurs comme ce sont les mêmes critères.
            cr.execute("UPDATE hr_employee "
                       "SET of_color_ft = ope.color_ft, of_color_bg = ope.color_bg, of_est_intervenant = True "
                       "FROM of_planning_equipe ope "
                       "JOIN of_planning_employee_rel oper ON ope.id = oper.equipe_id "
                       "JOIN hr_employee he ON oper.employee_id = he.id "
                       "WHERE hr_employee.id = he.id")

            # On recopie le choix des couleurs de l'utilisateur dans les employés.
            cr.execute("UPDATE hr_employee "
                       "SET of_color_ft = ru.of_color_ft, of_color_bg = ru.of_color_bg "
                       "FROM res_users ru "
                       "JOIN resource_resource rr ON ru.id = rr.user_id "
                       "JOIN hr_employee he ON rr.id = he.id "
                       "WHERE hr_employee.id = he.id "
                       "AND ru.of_color_ft != '#0D0D0D' "
                       "AND ru.of_color_bg != '#F0F0F0'")

            # Si le module of_planning_tournee est installé, on doit recopier les adresses de départ et de retour de l'équipe dans les employés.
            # Si un employé est membre de plusieurs équipes, ce sont les adresses de la dernière équipe renvoyée en SQL qui l'emportent.
            # Teste si le module of_planning_tournee est installé par l'existence du champ address_id.
            cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_planning_equipe' AND column_name = 'address_id'")
            if bool(cr.fetchall()):
                # Adresse de départ
                cr.execute("UPDATE hr_employee "
                           "SET of_address_depart_id = ope.address_id "
                           "FROM of_planning_equipe ope "
                           "JOIN of_planning_employee_rel oper ON ope.id = oper.equipe_id "
                           "JOIN hr_employee he ON oper.employee_id = he.id "
                           "WHERE hr_employee.id = he.id "
                           "AND ope.address_id IS NOT Null AND he.of_address_depart_id IS Null")
                # Adresse de retour
                cr.execute("UPDATE hr_employee "
                           "SET of_address_retour_id = ope.address_retour_id "
                           "FROM of_planning_equipe ope "
                           "JOIN of_planning_employee_rel oper ON ope.id = oper.equipe_id "
                           "JOIN hr_employee he ON oper.employee_id = he.id "
                           "WHERE hr_employee.id = he.id "
                           "AND ope.address_retour_id IS NOT Null AND he.of_address_retour_id IS Null")

            # On recopie les horaires des équipes dans les employés
            # dans le cas où ce n'est pas les horaires par défaut dans l'équipe et c'est les horaires par défaut dans l'employé.
            # Si un employé est membre de plusieurs équipes, ce sont les horaires de la dernière équipe renvoyée en SQL qui l'emportent.
            cr.execute("UPDATE hr_employee "
                       "SET of_hor_md = ope.hor_md, of_hor_mf = ope.hor_mf, of_hor_ad = ope.hor_ad, of_hor_af = ope.hor_af "
                       "FROM of_planning_equipe ope "
                       "JOIN of_planning_employee_rel oper ON ope.id = oper.equipe_id "
                       "JOIN hr_employee he ON oper.employee_id = he.id "
                       "WHERE hr_employee.id = he.id "
                       "AND NOT (ope.hor_md = 0 AND ope.hor_mf = 0 AND ope.hor_ad = 0 AND ope.hor_af = 0) "
                       "AND hr_employee.of_hor_md = 9 AND hr_employee.of_hor_mf = 12 AND hr_employee.of_hor_ad = 14 AND hr_employee.of_hor_af = 18")

            # On remplit le champ jours travaillés des employés par les valeurs lundi à vendredi pour les employés dont les jours ne sont pas déjà renseignés.
            cr.execute("INSERT INTO employee_jours_rel(employee_id, jour_id) "
                       "SELECT he.id, oj.id "
                       "FROM hr_employee he, of_jours oj "
                       "WHERE oj.numero >= 1 AND oj.numero <= 5 "
                       "AND he.id NOT IN (SELECT employee_id FROM employee_jours_rel)")

            # Initialisation des créneaux

            maintenant = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            # Horaires du matin
            cr.execute("INSERT INTO of_horaire_creneau(create_uid, write_uid, create_date, write_date, name, heure_debut, heure_fin, jour_number, jour_id) "
                       "SELECT DISTINCT ON(of_hor_md, of_hor_mf, oj.numero) 1, 1, '%s', '%s', oj.abr || ' ' || FLOOR(of_hor_md) || 'h' || REPLACE(RPAD(FLOOR(60*(of_hor_md-FLOOR(of_hor_md)))::text, 2, '0'), '00', '') || ' - ' || FLOOR(of_hor_mf) || 'h' || REPLACE(RPAD(FLOOR(60*(of_hor_mf-FLOOR(of_hor_mf)))::text, 2, '0'), '00', ''), of_hor_md, of_hor_mf, oj.numero, oj.id "
                       "FROM hr_employee he, employee_jours_rel ejr, of_jours oj "
                       "WHERE ejr.employee_id = he.id "
                       "AND ejr.jour_id = oj.id" % (maintenant, maintenant))
            # Horaires de l'après-midi
            cr.execute("INSERT INTO of_horaire_creneau(create_uid, write_uid, create_date, write_date, name, heure_debut, heure_fin, jour_number, jour_id) "
                       "SELECT DISTINCT ON(of_hor_ad, of_hor_af, oj.numero) 1, 1, '%s', '%s', oj.abr || ' ' || FLOOR(of_hor_ad) || 'h' || REPLACE(RPAD(FLOOR(60*(of_hor_ad-FLOOR(of_hor_ad)))::text, 2, '0'), '00', '') || ' - ' || FLOOR(of_hor_af) || 'h' || REPLACE(RPAD(FLOOR(60*(of_hor_af-FLOOR(of_hor_af)))::text, 2, '0'), '00', ''), of_hor_ad, of_hor_af, oj.numero, oj.id "
                       "FROM hr_employee he, employee_jours_rel ejr, of_jours oj "
                       "WHERE ejr.employee_id = he.id "
                       "AND ejr.jour_id = oj.id "
                       "AND (SELECT 1 FROM hr_employee WHERE hr_employee.of_hor_md = he.of_hor_ad AND hr_employee.of_hor_mf = he.of_hor_af) IS Null" % (maintenant, maintenant))
            # Initialisation des segments horaires
            cr.execute("INSERT INTO of_horaire_segment(create_uid, write_uid, create_date, write_date, employee_id, date_deb, date_fin, permanent, active) "
                       "SELECT 1, 1, '%s', '%s', id, '1970-01-01', Null, True, True "
                       "FROM hr_employee "
                       "WHERE of_est_intervenant = True" % (maintenant, maintenant))
            # Initialise lien entre créneau et segment
            cr.execute("INSERT INTO of_segment_creneau_rel(segment_id, creneau_id) "
                       "SELECT ohs.id, ohc.id "
                       "FROM of_horaire_segment ohs, hr_employee he, of_horaire_creneau ohc, employee_jours_rel ejr "
                       "WHERE ohs.employee_id = he.id "
                       "AND he.id = ejr.employee_id "
                       "AND((ohc.heure_debut = he.of_hor_md AND ohc.heure_fin = he.of_hor_mf AND ohc.jour_id = ejr.jour_id) "
                       "OR(ohc.heure_debut = he.of_hor_ad  AND ohc.heure_fin = he.of_hor_af AND ohc.jour_id = ejr.jour_id))")

            # On recopie les tâches des équipes vers les employés.
            cr.execute("INSERT INTO of_employee_tache_rel(employee_id, tache_id) "
                       "SELECT DISTINCT oper.employee_id, etr.tache_id "
                       "FROM equipe_tache_rel etr "
                       "JOIN of_planning_employee_rel oper ON etr.equipe_id = oper.equipe_id")

            # Si le module_of_service est installé :
            # 1) On désactive les services dont l'adresse d'intervention est inactive.
            # 2) On peuple le champ service_id dans les interventions
            # et supprime la colonne name pour que les valeurs soient recalculées à la mise à jour du module of_service
            # Règle retenue : on relie une intervention à un service quand les tâches du planning sont les mêmes
            # et que l'adresse de l'intervention est soit égale à l'adresse du service soit égale au client du service.
            # Teste si le module of_service est installé par l'existence du champ service_id.
            cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_planning_intervention' AND column_name = 'service_id'")
            if bool(cr.fetchall()):
                # Désactivation des services dont l'adresse est inactive.
                # À décommenter si décision de les désactiver.
                #cr.execute("UPDATE of_service "
                #           "SET active = False "
                #           "FROM res_partner "
                #           "WHERE of_service.address_id = res_partner.id "
                #           "AND res_partner.active = False")

                # Peuplement champ service_id
                cr.execute("UPDATE of_planning_intervention "
                           "SET service_id = of_service.id "
                           "FROM of_service "
                           "WHERE of_service.tache_id = of_planning_intervention.tache_id "
                           "AND (of_planning_intervention.address_id = of_service.address_id OR of_planning_intervention.address_id = of_service.partner_id)")
                cr.execute("ALTER TABLE of_service DROP COLUMN name")
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """
        Permettre la lecture de toutes les interventions d'un client depuis la fiche client
        """
        if self._context.get('force_read'):
            res = super(OfPlanningIntervention, self.sudo()).read(fields, load)
        else:
            res = super(OfPlanningIntervention, self).read(fields, load)
        return res

    @api.multi
    def check_access_rule(self, operation):
        """
        Permettre la lecture de toutes les interventions d'un client depuis la fiche client
        """
        if self._context.get('force_read') and operation == 'read':
            res = super(OfPlanningIntervention, self.sudo()).check_access_rule(operation)
        else:
            res = super(OfPlanningIntervention, self).check_access_rule(operation)
        return res

    @api.model
    def _modifier_droits_existants_utilisateurs(self):
        u"""Initialise les droits planning des utilisateurs existants à la 1ère mise à jour du module"""
        # Un changement des droit a été fait durant la vie du module.
        # Cette fonction effectue un transfert de l'ancien droit vers les nouveaux.
        # Elle est appelée à chaque mise à jour du module mais un test sur l'existance de l'ancien droit permet qu'elle ne s'exécute que lors de la 1ère mise à jour.
        # Règles de conversion :
        # Ancien droit "Utilisateur : mes interventions seulement" -> Nouveau droit lecture "Voir mes interventions seulement" et nouveau droit modification vide
        # Ancien droit "Utilisateur : toutes les interventions" -> Nouveau droit lecture "Voir toutes les interventions" et nouveau droit modification vide
        # Ancien droit "Responsable" -> Nouveau droit lecture "Voir toutes les interventions" et nouveau droit modification "Modifier toutes les interventions"

        cr = self._cr
        # On teste si l'ancien groupe de droit existe (si oui, c'est la 1ère mise à jour du module)
        cr.execute("SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_user_restrict'")
        if bool(cr.fetchall()):
            # On récupère la liste des utilisateurs qui ont l'ancien droit "Utilisateur : mes interventions seulement".
            cr.execute("SELECT ru.id "
                       "FROM res_groups_users_rel AS rel, res_users AS ru, res_groups AS rg "
                       "WHERE rel.gid = (SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_user_restrict' LIMIT 1)"
                       "AND ru.id = rel.uid "
                       "AND rg.id = rel.gid")
            user_restrict_ids = [x[0] for x in cr.fetchall()]

            # On récupère la liste des utilisateurs qui ont l'ancien droit "Utilisateur : toutes les interventions".
            cr.execute("SELECT ru.id "
                       "FROM res_groups_users_rel AS rel, res_users AS ru, res_groups AS rg "
                       "WHERE rel.gid = (SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_user' LIMIT 1) "
                       "AND ru.id = rel.uid "
                       "AND rg.id = rel.gid")
            user_ids = [x[0] for x in cr.fetchall()]

            # On récupère la liste des utilisateurs qui ont l'ancien droit "Responsable".
            cr.execute("SELECT ru.id "
                       "FROM res_groups_users_rel AS rel, res_users AS ru, res_groups AS rg "
                       "WHERE rel.gid = (SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_manager' LIMIT 1) "
                       "AND ru.id = rel.uid "
                       "AND rg.id = rel.gid")
            manager_ids = [x[0] for x in cr.fetchall()]

            # On ajoute les utilisateurs de l'ancien droit "mes interventions seulement" au nouveau droit "Voir mes interventions seulement".
            # On récupère l'id du nouveau droit.
            cr.execute("SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_lecture_siens' LIMIT 1")
            group_id = cr.fetchone()[0]
            # On les ajoute.
            if group_id and user_restrict_ids:
                cr.execute("INSERT INTO res_groups_users_rel (gid, uid) " + "SELECT " + str(group_id) + ", uid FROM unnest(array[" + ', '.join(str(x) for x in user_restrict_ids) + "]) g(uid)")

            # On ajoute les utilisateurs de l'ancien droit "toutes les interventions" au nouveau droit "Voir toutes les interventions".
            cr.execute("SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_lecture_tout' LIMIT 1")
            group_id = cr.fetchone()[0]
            if group_id and user_ids:
                cr.execute("INSERT INTO res_groups_users_rel (gid, uid) " + "SELECT " + str(group_id) + ", uid FROM unnest(array[" + ', '.join(str(x) for x in user_ids) + "]) g(uid)")

            # On ajoute les utilisateurs de l'ancien droit "Responsable" au nouveau droit "Modifier mes interventions seulement".
            cr.execute("SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_modification_siens' LIMIT 1")
            group_id = cr.fetchone()[0]
            if group_id and manager_ids:
                cr.execute("INSERT INTO res_groups_users_rel (gid, uid) " + "SELECT " + str(group_id) + ", uid FROM unnest(array[" + ', '.join(str(x) for x in manager_ids) + "]) g(uid)")

            # On ajoute les utilisateurs de l'ancien droit "Responsable" au nouveau droit "Modifier toutes les interventions".
            cr.execute("SELECT res_id FROM ir_model_data WHERE name = 'of_group_planning_intervention_modification_tout' LIMIT 1")
            group_id = cr.fetchone()[0]
            if group_id and manager_ids:
                cr.execute("INSERT INTO res_groups_users_rel (gid, uid) " + "SELECT " + str(group_id) + ", uid FROM unnest(array[" + ', '.join(str(x) for x in manager_ids) + "]) g(uid)")

        return True

    @api.depends('employee_ids')
    def _compute_tz(self):
        for intervention in self:
            if intervention.employee_ids:
                intervention.tz = intervention.employee_ids[0].of_tz

    @api.depends('date', 'duree', 'employee_ids', 'forcer_dates')
    def _compute_date_deadline(self):
        compare_precision = 5
        employee_obj = self.env['hr.employee']
        for intervention in self:
            if not (intervention.employee_ids and intervention.date and intervention.duree):
                continue

            if intervention.forcer_dates:
                intervention.date_deadline = intervention.date_deadline_forcee
            else:

                employees = intervention.employee_ids
                tz = pytz.timezone(intervention.tz)
                if not tz:
                    tz = "Europe/Paris"

                # Génération courante_da
                date_utc_dt = datetime.strptime(intervention.date, "%Y-%m-%d %H:%M:%S")  # Datetime UTC
                date_locale_dt = fields.Datetime.context_timestamp(intervention, date_utc_dt)  # Datetime local
                date_locale_str = fields.Datetime.to_string(date_locale_dt).decode('utf-8')  # String Datetime local
                date_courante_da = fields.Date.from_string(date_locale_str)  # Date local
                date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')
                un_jour = timedelta(days=1)

                une_semaine = timedelta(days=7)
                date_stop_dt = date_locale_dt + une_semaine  # Pour des raisons pratiques on limite la recherche des horaires à une semaine après la date d'intervention
                date_stop_str = fields.Datetime.to_string(date_stop_dt).decode('utf-8')
                # Récupérer le dictionnaire des segments horaires des employés
                horaires_list_dict = employees.get_horaires_list_dict(date_locale_str, date_stop_str)
                # Récupérer la liste des segments de l'équipe (ie l'intersection des horaires des employés)
                segments_equipe = employees.get_list_horaires_intersection(horaires_list_dict=horaires_list_dict)

                jour_courant = date_locale_dt.isoweekday()

                duree_restante = intervention.duree
                heure_debut = date_locale_dt.hour + (date_locale_dt.minute + date_locale_dt.second / 60.0) / 60.0  # heure en float

                # Vérifier que l'intervention commence sur un créneau travaillé
                index_creneau = employee_obj.debut_sur_creneau(date_courante_str, heure_debut, segments_equipe)
                if index_creneau == -1:
                    raise UserError(u"L'horaire de début des travaux est en dehors des heures de travail.")

                heure_courante = heure_debut
                segment_courant = segments_equipe.pop(0)
                horaires_dict = segment_courant[2]
                while float_compare(duree_restante, 0.0, compare_precision) > 0.0:

                    fin_creneau_courant = horaires_dict[jour_courant][index_creneau][1]
                    if float_compare(fin_creneau_courant, heure_courante + duree_restante, compare_precision) >= 0.0:
                        # L'intervention se termine sur ce créneau
                        heure_courante += duree_restante
                        break
                    # L'intervention continue.
                    # Y-a-t-il un créneau suivant la même journée ?
                    if index_creneau + 1 < len(horaires_dict[jour_courant]):  # oui
                        duree_restante -= (horaires_dict[jour_courant][index_creneau][1] - heure_courante)
                        index_creneau += 1
                        heure_courante = horaires_dict[jour_courant][index_creneau][0]
                        continue
                    # Il n'y a pas de créneau suivant la même journée : terminer la journée puis passer au jour suivant.
                    duree_restante -= (horaires_dict[jour_courant][index_creneau][1] - heure_courante)

                    jour_courant = ((jour_courant + 1) % 7) or 7  # num jour de la semaine entre 1 et 7
                    date_courante_da += un_jour
                    date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')

                    if date_courante_str > segment_courant[1] and len(segments_equipe) > 0:  # Changer de segment courant
                        segment_courant = segments_equipe.pop(0)
                        horaires_dict = segment_courant[2]

                    while jour_courant not in horaires_dict or horaires_dict[jour_courant] == []:  # On saute les jours non travaillés.
                        jour_courant = ((jour_courant + 1) % 7) or 7  # num jour de la semaine entre 1 et 7
                        #date_courante_deb_dt += un_jour
                        date_courante_da += un_jour
                        if date_courante_str > segment_courant[1] and len(segments_equipe) > 0:  # Changer de segment courant
                            segment_courant = segments_equipe.pop(0)
                            horaires_dict = segment_courant[2]

                    index_creneau = 0
                    # Heure_courante passée à l'heure de début du premier créneau du jour travaillé suivant
                    heure_courante = horaires_dict[jour_courant][index_creneau][0]

                # La durée restante est égale à 0 ! on y est !
                date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')  # String date courante locale
                date_courante_deb_dt = tz.localize(datetime.strptime(date_courante_str+" 00:00:00", "%Y-%m-%d %H:%M:%S"))  # Datetime local début du jour
                # Calcul de la nouvelle date
                date_deadline_locale_dt = date_courante_deb_dt + timedelta(hours=heure_courante)
                # Conversion en UTC
                date_deadline_utc_dt = date_deadline_locale_dt - date_deadline_locale_dt.tzinfo._utcoffset
                date_deadline_str = date_deadline_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                intervention.date_deadline = date_deadline_str


    @api.depends('address_id', 'address_id.parent_id')
    def _compute_partner_id(self):
        for intervention in self:
            partner = intervention.address_id or False
            if partner:
                while partner.parent_id:
                    partner = partner.parent_id
            intervention.partner_id = partner and partner.id

    @api.depends('description')
    def _compute_cleantext_description(self):
        cleanr = re.compile('<.*?>')
        for interv in self:
            cleantext = re.sub(cleanr, '', interv.description or '')
            interv.cleantext_description = cleantext

    @api.depends('order_id.of_notes_intervention')
    def _compute_cleantext_intervention(self):
        cleanr = re.compile('<.*?>')
        for interv in self:
            cleantext = re.sub(cleanr, '', interv.order_id.of_notes_intervention or '')
            interv.cleantext_intervention = cleantext

    @api.depends('date', 'date_deadline_forcee')
    def _compute_jour(self):
        for inter in self:
            t = ''
            if inter.date:
                dt = datetime.strptime(inter.date, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)  # openerp's ORM method
                t = dt.strftime("%A").capitalize()  # The day_name is Sunday here.
            inter.jour = t
            t_fin = ''
            if inter.date_deadline:
                dt = datetime.strptime(inter.date_deadline, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)  # openerp's ORM method
                t_fin = dt.strftime("%A").capitalize()  # The day_name is Sunday here.
            inter.jour_fin = t_fin
            t_fin_force = ''
            if inter.date_deadline_forcee:
                dt = datetime.strptime(inter.date_deadline_forcee, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)  # openerp's ORM method
                t_fin_force = dt.strftime("%A").capitalize()  # The day_name is Sunday here.
            inter.jour_fin_force = t_fin_force

    @api.depends('date')
    def _compute_date_date(self):
        for inter in self:
            inter.date_date = inter.date

    @api.multi
    @api.depends('employee_ids')
    def _compute_employee_main_id(self):
        for inter in self:
            if inter.employee_ids:
                inter.employee_main_id = inter.employee_ids[0]

    def _search_gb_employee_id(self, operator, value):
        return [('employee_ids', operator, value)]

    @api.model
    def _search_date_date(self, operator, value):
        mode = self._context.get('of_date_search_mode')
        if mode in ('week', 'month'):
            date = fields.Date.from_string(value)
            if mode == 'week':
                date_start = date - timedelta(days=date.weekday())
                date_stop = date_start + timedelta(days=7)
            else:
                date_start = date - timedelta(days=date.day)
                date_stop = date_start + relativedelta(months=1)
            domain = ['&',
                      ('date_deadline', '>=', fields.Date.to_string(date_start)),
                      ('date', '<', fields.Date.to_string(date_stop))]
        else:
            if operator == '=':
                domain = ['&', ('date_deadline', '>=', value), ('date', '<=', value)]
            elif operator == '!=':
                domain = ['|', ('date', '<', value), ('date_deadline', '>', value)]
            elif operator in ('<', '<='):
                domain = [('date', operator, value)]
            else:
                domain = [('date_deadline', operator, value)]
        return domain

    @api.depends('state')
    def _compute_state_int(self):
        for interv in self:
            if interv.state and interv.state == 'draft':
                interv.state_int = 0
            elif interv.state and interv.state == 'confirm':
                interv.state_int = 1
            elif interv.state and interv.state in ('done', 'unfinished'):
                interv.state_int = 2
            elif interv.state and interv.state in ('cancel', 'postponed'):
                interv.state_int = 3

    @api.depends('name', 'number')
    def _compute_calendar_name(self):
        for intervention in self:
            intervention.calendar_name = intervention.number and ' - '.join([intervention.number, intervention.name]) or intervention.name

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.state == "draft" and self.template_id:
            self.tache_id = self.template_id.tache_id

    @api.multi
    def of_get_report_name(self, docs):
        return "Rapport d'intervention"

    @api.multi
    def of_get_report_number(self, docs):
        return self.number

    @api.multi
    def of_get_report_date(self, docs):
        planning_date = fields.Datetime.from_string(self.date)
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        return planning_date.strftime(lang.date_format)

    @api.model
    def get_state_int_map(self):
        v0 = {'label': 'Brouillon', 'value': 0}
        v1 = {'label': u'Confirmé', 'value': 1}
        v2 = {'label': u'Réalisé / Inachevé', 'value': 2}
        v3 = {'label': u'Annulé / Reporté', 'value': 3}
        return (v0, v1, v2, v3)

    @api.onchange('address_id')
    def _onchange_address_id(self):
        name = False
        if self.address_id:
            name = [self.address_id.name_get()[0][1]]
            for field in ('zip', 'city'):
                val = getattr(self.address_id, field)
                if val:
                    name.append(val)
        self.name = name and " ".join(name) or "Intervention"

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        if self.tache_id and self.tache_id.duree:
            self.duree = self.tache_id.duree
            if self.employee_ids and not self.employee_ids.peut_faire(self.tache_id):
                raise UserError("Aucun des intervenants de cette intervention ne peut réaliser cette Tâche")

    @api.onchange('forcer_dates')
    def _onchange_forcer_dates(self):
        if self.forcer_dates:
            heures, minutes = float_2_heures_minutes(self.duree)
            self.date_deadline_forcee = fields.Datetime.to_string(fields.Datetime.from_string(self.date) +
                                                                  relativedelta(hours=heures, minutes=minutes))
        print "OYE"

    @api.onchange('date_deadline_forcee', 'date', 'duree')
    def _onchange_date_deadline_forcee(self):
        #if self.date_deadline_forcee and self.forcer_dates and self.date and self.duree:
        #    diff_heures = relativedelta(fields.Datetime.from_string(self.date_deadline_forcee), fields.Datetime.from_string(self.date))
        if not self.check_coherence_dates():
            raise UserError(u"Attention /!\ la date de fin doit être au moins égale à la date de début + la durée")

    """@api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        self.ensure_one()
        employee = self.employee_main_id
        if employee:
            self.hor_md = employee.of_hor_md
            self.hor_mf = employee.of_hor_mf
            self.hor_ad = employee.of_hor_ad
            self.hor_af = employee.of_hor_af
            emp_jours_ids = employee.of_jour_ids._ids
            if not emp_jours_ids:
                emp_jours_ids = self.env['of.jours'].search([('numero', 'in', [1, 2, 3, 4, 5])])._ids
            self.jour_ids = [(5, 0, 0)] + [(4, le_id, 0) for le_id in emp_jours_ids]
            self.of_creneau_ids = [(5, 0, 0)] + [(4, le_id, 0) for le_id in employee.of_creneau_ids._ids]
            self.of_creneau_temp_ids = [(5, 0, 0)] + [(4, le_id, 0) for le_id in employee.of_creneau_temp_ids._ids]
            self.of_creneau_temp_start = employee.of_creneau_temp_start
            self.of_creneau_temp_stop = employee.of_creneau_temp_stop
            self.mode_horaires = employee.of_mode_horaires"""

    @api.onchange('equipe_id')
    def _onchange_equipe_id(self):
        self.ensure_one()
        if self.equipe_id:
            self.employee_ids = [(5, 0, 0)] + [(4, id_emp, 0) for id_emp in self.equipe_id.employee_ids._ids]

    @api.multi
    def button_confirm(self):
        return self.write({'state': 'confirm'})

    @api.multi
    def button_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def button_unfinished(self):
        return self.write({'state': 'unfinished'})

    @api.multi
    def button_postponed(self):
        return self.write({'state': 'postponed'})

    @api.multi
    def button_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def button_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def do_verif_dispo(self):
        # Vérification de la validité du créneau
        intervention_obj = self.env['of.planning.intervention']
        for intervention in self:
            if intervention.verif_dispo:
                rdv = intervention_obj.search([
                    ('employee_ids', 'in', intervention.employee_ids.ids),  # /!\ conserver .ids : ._ids est un tuple et génère une erreur à l'évaluation
                    ('date', '<', intervention.date_deadline),
                    ('date_deadline', '>', intervention.date),
                    ('id', '!=', intervention.id),
                    ('state', 'not in', ('cancel', 'postponed')),
                ], limit=1)
                if rdv:
                    raise ValidationError(u'L\'employé %s a déjà au moins un rendez-vous sur ce créneau.' % ((rdv.employee_ids & intervention.employee_ids))[0].name)

    @api.multi
    def _affect_number(self):
        for interv in self:
            if interv.template_id and interv.state in ('confirm', 'done', 'unfinished', 'postponed') and not interv.number:
                interv.write({'number': self.template_id.sequence_id.next_by_id()})

    @api.model
    def create(self, vals):
        if 'date' in vals:
            # Tronqué à la minute
            date = vals['date'][:17] + '00'
        res = super(OfPlanningIntervention, self).create(vals)
        res.do_verif_dispo()
        res._affect_number()
        return res

    @api.multi
    def write(self, vals):
        # @todo: @GF finir ce code + Attention !
        # # En cas de modification des horaires d'un employé, toutes les interventions aux dates concernées
        # # par le changement doivent être passée en dates forcées. Dans le cas ou une intervention aurait sa
        # # date de début qui ne serait plus sur des créneaux, cette intervention ne serait plus modifiable
        # if vals.get("forcer_dates", None) != None and not vals.get("date_deadline_forcee", False):
        #     for intervention in self:
        #         intervention.write({
        #             'forcer_dates': True,
        #             'date_deadline_forcee': intervention.date_deadline,
        #         })
        # else:
        if 'date' in vals:
            # Tronqué à la minute
            date = vals['date'][:17] + '00'
        super(OfPlanningIntervention, self).write(vals)
        self.do_verif_dispo()
        self._affect_number()
        return True

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'gb_employee_id':
            return super(OfPlanningIntervention, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'of_planning_employee_rel', 'equipe_id', 'equipe_id', 'equipe_id'),
            implicit=False, outer=True,
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".employee_id' % (alias,)
        }

    @api.multi
    def _get_invoicing_company(self, partner):
        return self.company_id or partner.company_id

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()

        msg_succes = u"SUCCES : création de la facture depuis l'intervention %s"
        msg_erreur = u"ÉCHEC : création de la facture depuis l'intervention %s : %s"

        partner = self.partner_id
        err = []
        if not partner:
            err.append("sans partenaire")
        product = self.tache_id.product_id
        if not product:
            err.append(u"pas de produit lié")
        elif product.type != 'service':
            err.append(u"le produit lié doit être de type 'Service'")
        if err:
            return (False,
                    msg_erreur % (self.name, ", ".join(err)))
        fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(partner.id, delivery_id=self.address_id.id)
        if not fiscal_position_id:
            return (False,
                    msg_erreur % (self.name, u"pas de position fiscale définie pour le partenaire ni pour la société"))

        # Préparation de la ligne de facture
        taxes = product.taxes_id
        if partner.company_id:
            taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
        taxes = self.env['account.fiscal.position'].browse(fiscal_position_id).map_tax(taxes, product, partner)

        line_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not line_account:
            return (False,
                    msg_erreur % (self.name, u'Il faut configurer les comptes de revenus pour la catégorie du produit.\n'))

        # Mapping des comptes par taxe induit par le module of_account_tax
        for tax in taxes:
            line_account = tax.map_account(line_account)

        pricelist = partner.property_product_pricelist
        company = self._get_invoicing_company(partner)

        if pricelist.discount_policy == 'without_discount':
            from_currency = company.currency_id
            price_unit = from_currency.compute(product.lst_price, pricelist.currency_id)
        else:
            price_unit = product.with_context(pricelist=pricelist.id).price
        price_unit = self.env['account.tax']._fix_tax_included_price(price_unit, product.taxes_id, taxes)

        line_data = {
            'name': product.name_get()[0][1],
            'origin': 'Intervention',
            'account_id': line_account.id,
            'price_unit': price_unit,
            'quantity': 1.0,
            'discount': 0.0,
            'uom_id': product.uom_id.id,
            'product_id': product.id,
            'invoice_line_tax_ids': [(6, 0, taxes._ids)],
        }

        journal_id = self.env['account.invoice'].with_context(company_id=company.id).default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(u"Vous devez définir un journal des ventes pour cette société (%s)." % company.name)
        invoice_data = {
            'origin': 'Intervention',
            'type': 'out_invoice',
            'account_id': partner.property_account_receivable_id.id,
            'partner_id': partner.id,
            'partner_shipping_id': self.address_id.id,
            'journal_id': journal_id,
            'currency_id': pricelist.currency_id.id,
            'fiscal_position_id': fiscal_position_id,
            'company_id': company.id,
            'user_id': self._uid,
            'invoice_line_ids': [(0, 0, line_data)],
        }

        return (invoice_data,
                msg_succes % (self.name,))

    @api.multi
    def create_invoice(self):
        invoice_obj = self.env['account.invoice']

        msgs = []
        for intervention in self:
            invoice_data, msg = intervention._prepare_invoice()
            msgs.append(msg)
            if invoice_data:
                invoice = invoice_obj.create(invoice_data)
                invoice.compute_taxes()
                invoice.message_post_with_view('mail.message_origin_link',
                                               values={'self': invoice, 'origin': intervention},
                                               subtype_id=self.env.ref('mail.mt_note').id)
        msg = "\n".join(msgs)

        return {
            'name'     : u'Création de la facture',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.planning.message.invoice',
            'type'     : 'ir.actions.act_window',
            'target'   : 'new',
            'context'  : {'default_msg': msg}
        }

class OFInterventionConfiguration(models.TransientModel):
    u"""modèle défini ici, utilisé par of_planning_view"""
    _name = 'of.intervention.settings'
    _inherit = 'res.config.settings'

class ResPartner(models.Model):
    _inherit = "res.partner"

    intervention_partner_ids = fields.One2many('of.planning.intervention', string="Interventions client", compute="_compute_interventions")
    intervention_address_ids = fields.One2many('of.planning.intervention', string="Interventions adresse", compute="_compute_interventions")

    @api.multi
    def _compute_interventions(self):
        intervention_obj = self.sudo().env['of.planning.intervention']
        for partner in self:
            partner.intervention_partner_ids = intervention_obj.search([('partner_id', '=', partner.id)])
            partner.intervention_address_ids = intervention_obj.search([('address_id', '=', partner.id)])

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Utilisé pour ajouter bouton Interventions à Devis (see order_id many2one field above)
    intervention_ids = fields.One2many("of.planning.intervention", "order_id", string="Interventions")

    intervention_count = fields.Integer(string='Interventions', compute='_compute_intervention_count')

    @api.depends('intervention_ids')
    @api.multi
    def _compute_intervention_count(self):
        for sale_order in self:
            sale_order.intervention_count = len(sale_order.intervention_ids)

    @api.multi
    def action_view_interventions(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]

        action['domain'] = [('order_id', 'in', self._ids)]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context.update({
                'default_address_id': self.partner_shipping_id.id or False,
                'default_order_id': self.id,
            })
            action['context'] = str(context)
        return action

class OfPlanningInterventionTemplate(models.Model):
    _name = 'of.planning.intervention.template'

    name = fields.Char(string=u"Nom du modèle", required=True)
    active = fields.Boolean(string="Active", default=True)
    code = fields.Char(string="Code", compute="_compute_code", inverse="_inverse_code", store=True, required=True)
    sequence_id = fields.Many2one('ir.sequence', string=u"Séquence", readonly=True)
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche")

    @api.depends('sequence_id')
    def _compute_code(self):
        for template in self:
            template.code = template.sequence_id.prefix

    def _inverse_code(self):
        sequence_obj = self.env['ir.sequence']
        for template in self:
            if not template.code:
                continue
            sequence_name = u"Modèle d'intervention " + template.code
            sequence_code = self._name
            # Si une séquence existe déjà avec ce code, on la reprend
            sequence = sequence_obj.search([('code', '=', sequence_code), ('prefix', '=', self.code)])
            if sequence:
                template.sequence_id = sequence
                continue

            if template.sequence_id:
                # Si la séquence n'est pas utilisée par un autre modèle, on la modifie directement,
                # sinon il faudra en re-créer une.
                if not self.search([('sequence_id', '=', template.sequence_id.id), ('id', '!=', template.id)]):
                    template.sequence_id.sudo().write({'prefix': template.code, 'name': sequence_name})
                    continue

            # Création d'une séquence pour le modèle
            sequence_data = {
                'name': sequence_name,
                'code': sequence_code,
                'implementation': 'no_gap',
                'prefix': template.code,
                'padding': 4,
            }
            template.sequence_id = self.env['ir.sequence'].sudo().create(sequence_data)

class OfPlanningTag(models.Model):
    _description = u"Étiquettes d'intervention"
    _name = 'of.planning.tag'

    name = fields.Char(string='Nom', required=True, translate=True)
    color = fields.Integer(string='Index couleur')
    active = fields.Boolean(default=True, help=u"Permet de cacher l'étiquette sans la supprimer.")
    intervention_ids = fields.Many2many(
        'of.planning.intervention', column1='tag_id', column2='intervention_id', string='Interventions')

class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        if report_name == 'of_planning.of_planning_fiche_intervention_report_template':
            self = self.sudo()
        result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        return result
