# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import re
import requests
import urllib
import base64

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config, DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval

import odoo.addons.decimal_precision as dp
from odoo.addons.of_utils.models.of_utils import float_2_heures_minutes, compare_date, hours_to_strs


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class HREmployee(models.Model):
    _inherit = "hr.employee"

    of_tache_ids = fields.Many2many('of.planning.tache', 'of_employee_tache_rel', 'employee_id', 'tache_id', u"Tâches")
    of_toutes_taches = fields.Boolean(string=u"Apte à toutes les tâches")
    of_equipe_ids = fields.Many2many(
        'of.planning.equipe', 'of_planning_employee_rel', 'employee_id', 'equipe_id', u"Équipes")
    of_est_intervenant = fields.Boolean(string=u"Est intervenant", default=False)
    of_est_commercial = fields.Boolean(string=u"Est commercial", default=False)
    of_impression_planning = fields.Boolean(string=u"Impression planning", default=True)
    of_daily_email = fields.Boolean(
        string=u"Envoi email veille de RDV", default=False,
        help=u"Active l'envoi chaque soir du planning au courriel de l'employé, quand celui-ci a des RDV le lendemain.")

    @api.onchange('of_est_intervenant', 'of_est_commercial')
    def _onchange_est_intervenant(self):
        self.ensure_one()
        if not self.of_est_intervenant and not self.of_est_commercial:
            self.of_impression_planning = False

    @api.onchange('of_daily_email')
    def _onchange_of_daily_email(self):
        self.ensure_one()
        if self.of_daily_email:
            self.of_impression_planning = True

    @api.onchange('of_impression_planning')
    def _onchange_of_impression_planning(self):
        self.ensure_one()
        if not self.of_impression_planning:
            self.of_daily_email = False

    @api.multi
    def peut_faire(self, tache, all_required=False):
        """
        Renvoie True si les employés dans self peuvent réaliser la tâche. Sauf si all_required=True, il suffit qu'un
        des employés puisse réaliser la tâche pour que la fonction renvoie True
        :param tache: La tâche en question
        :param all_required: True si tous les employés doivent savoir réaliser la tâche
        :return: True si peut faire, False sinon
        :rtype Boolean
        """
        if all_required:
            return len(self.filtered(lambda e: (tache not in e.of_tache_ids) and not e.of_toutes_taches)) == 0
        return len(self.filtered(lambda e: (tache in e.of_tache_ids) or e.of_toutes_taches))

    @api.multi
    def get_taches_possibles(self, en_commun=False):
        """
        Renvoie la liste des tâches possibles pour self, en prenant en compte le champ of_toutes_taches
        :param en_commun: à True pour ne renvoyer que les tâches que tout self peut faire
        :return: liste des tâches possibles
        :rtype env['of.planning.tache']
        """
        self = self.filtered(lambda e: not e.of_toutes_taches)
        if not self:
            return self.env['of.planning.tache'].search([])
        taches = self.mapped('of_tache_ids')
        if not en_commun:
            return taches
        for employee in self:
            taches = taches.filtered(lambda t: t.id in employee.of_tache_ids.ids)
        return taches

    @api.multi
    def name_get(self):
        """Permet dans un RDV d'intervention de proposer les intervenants inaptes entre parenthèses"""
        # Ajout d'un sudo pour éviter des erreurs à l'affichage pour les intervenants d'autres sociétés.
        self = self.sudo()
        result = super(HREmployee, self).name_get()
        tache_id = self._context.get('tache_prio_id')
        if not tache_id:
            return result
        tache = self.env['of.planning.tache'].browse(tache_id)
        for i, vals in enumerate(result):
            if not self.browse(vals[0]).peut_faire(tache):
                result[i] = (vals[0], "(" + vals[1] + ")")
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un RDV d'intervention de proposer en priorité les intervenants aptes à la tâche"""
        if self._context.get('tache_prio_id'):
            tache_id = self._context.get('tache_prio_id')
            args = args or []
            res = super(HREmployee, self).name_search(
                name,
                args + ['|', ['of_tache_ids', 'in', tache_id], ['of_toutes_taches', '=', True]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(HREmployee, self).name_search(
                name,
                args + [['of_tache_ids', 'not in', tache_id], ['of_toutes_taches', '=', False]],
                operator,
                limit) or []
            return res
        return super(HREmployee, self).name_search(name, args, operator, limit)

    @api.model
    def send_next_day_planning(self):
        template_id = self.env.ref('of_planning.email_template_planning_jour_demain')
        next_day_da = fields.Date.from_string(fields.Date.today()) + timedelta(days=1)
        next_day_str = fields.Date.to_string(next_day_da)
        interventions = self.env['of.planning.intervention'].with_context(virtual_id=True).search([
            ('date', '>=', next_day_str),
            ('date_deadline', '<=', next_day_str),
            ('state', 'not in', ['draft', 'postponed', 'cancel']),
        ])
        employees = interventions.mapped('employee_ids').filtered(
            lambda e: e.of_impression_planning and e.of_daily_email)
        wiz_vals = {'type': 'day', 'date_start': next_day_str, }
        impression_wizard = self.env['of_planning.impression_wizard'].create(wiz_vals)
        # Pour chaque employé, générer le PDF et envoyer l'email
        for employee in employees:
            impression_wizard.employee_ids = [(6, 0, [employee.id])]
            email_values = {}
            # création du pdf et ajout dans les values, il sera automatiquement joint à l'email envoyé
            planning_pdf = self.env['report'].get_pdf(impression_wizard.ids, 'of_planning.report_of_planning_jour')
            attachment = self.env['ir.attachment'].create({
                'name': u"planning_%s" % next_day_str,
                'datas_fname': u"planning_%s_%s.pdf" % (employee.name, next_day_str),
                'type': 'binary',
                'datas': base64.encodestring(planning_pdf),
                'res_model': 'of_planning.impression_wizard',
                'res_id': impression_wizard.id,
                'mimetype': 'application/x-pdf'
            })
            email_values['attachment_ids'] = attachment.ids
            # envoi immédiat de l'email
            template_id.send_mail(employee.id, force_send=True, email_values=email_values)

        return True


class OfPlanningTacheCateg(models.Model):
    _name = "of.planning.tache.categ"
    _description = u"Planning OpenFire : Catégories de tâches"
    _order = "sequence, id"

    name = fields.Char(u"Libellé", size=64, required=True)
    description = fields.Text("Description")
    tache_ids = fields.One2many('of.planning.tache', 'tache_categ_id', string=u"Tâches")
    active = fields.Boolean("Actif", default=True)
    sequence = fields.Integer(u"Séquence", help=u"Ordre d'affichage (plus petit en premier)")
    color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D")
    color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0")

    fourchette_planif = fields.Selection(
        [
            ('semaine', u"À la semaine"),
            ('quinzaine', u"À la quinzaine"),
            ('mois', u"Au mois"),
        ], string=u"Granularité de planif",
        help=u"""
La granularité permet de définir la période de planification de référence par type de tâche.\n
Cette granularité permet, à la saisie d'une demande d'intervention,
de calculer la date de fin une fois la date de début saisie. par défaut :\n
  * Pour une pose la granularité de planification est la quinzaine\n
  * Pour un SAV (quand le champ SAV est rempli), la granularité de planification est la semaine\n
  * Pour un entretien (intervention récurrente), la granularité de planification est le mois\n
""")

    @api.model
    def get_caption_data(self):
        data = {}
        categs = self.search([])
        for categ in categs:
            data[categ.id] = {
                'value': categ.id,
                'label': categ.name,
                'color_bg': categ.color_bg,
                'color_ft': categ.color_ft,
            }
        data[-1] = {
            'value': -1,
            'label': u"Sans catégorie",
            'color_bg': u"#F0F0F0",
            'color_ft': u"#0D0D0D",
        }
        return data


class OfPlanningTache(models.Model):
    _name = "of.planning.tache"
    _description = u"Planning OpenFire : Tâches"
    _order = 'sequence'

    name = fields.Char(string=u"Libellé", size=100, required=True)
    description = fields.Text("Description")
    sequence = fields.Integer(string="Sequence", default=1, help="Used to order tasks. Lower is better.")
    affichage = fields.Selection([
        ('hide', u"Ne pas afficher"),
        ('internal_description', u"Dans la description interne"),
        ('external_description', u"Dans la description externe"),
    ], string=u"Affichage description", default='internal_description')
    verr = fields.Boolean(u"Verrouillé")
    product_id = fields.Many2one('product.product', "Produit")
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Position fiscale", company_dependent=True)
    active = fields.Boolean("Actif", default=True)
    imp_detail = fields.Boolean(u'Imprimer Détail', help=u"""Impression du détail des tâches dans le planning semaine
Si cette option n'est pas cochée, seule la tâche la plus souvent effectuée dans la journée apparaîtra""", default=True)
    duree = fields.Float(u'Durée par défaut', digits=(12, 5), default=1.0)
    tache_categ_id = fields.Many2one('of.planning.tache.categ', string=u"Catégorie de tâche")
    is_crm = fields.Boolean(u"Tâche CRM")
    equipe_ids = fields.Many2many(
        'of.planning.equipe', 'equipe_tache_rel', 'tache_id', 'equipe_id', u"Équipes qualifiées")
    employee_ids = fields.Many2many(
        'hr.employee', string=u"Employés qualifiés", compute="_compute_employee_ids", search="_search_employee_ids")
    category_id = fields.Many2one('hr.employee.category', string=u"Catégorie d'employés")
    fourchette_planif = fields.Selection(related="tache_categ_id.fourchette_planif", readonly=True)
    flexible = fields.Boolean(string="Flexible")

    @api.multi
    def _compute_employee_ids(self):
        intervenants = self.env['hr.employee'].search(
            ['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)])
        for tache in self:
            tache.employee_ids = intervenants.filtered(lambda i: i.of_toutes_taches or tache.id in i.of_tache_ids.ids)

    def _search_employee_ids(self, operator, value):
        """/!\\ Seuls les cas 'in' et 'not in' sont traités"""
        taches = self.search([])

        if operator == 'in':
            taches = taches.filtered(lambda t: set(t.employee_ids.ids).intersection(value))
        elif operator == 'not in':
            taches = taches.filtered(lambda t: not set(t.employee_ids.ids).intersection(value))

        return [('id', 'in', taches.ids)]

    @api.multi
    def unlink(self):
        if self.search([('id', 'in', self._ids), ('verr', '=', True)]):
            raise ValidationError(u"Vous essayez de supprimer une tâche verrouillée.")
        return super(OfPlanningTache, self).unlink()

    @api.multi
    def name_get(self):
        """Permet dans un RDV d'intervention de proposer les taches non faisables entre parenthèses"""
        intervenant_ids = self._context.get('intervenant_prio_ids')
        if intervenant_ids:
            intervenants = self.env['hr.employee'].browse(intervenant_ids[0][2]) or []  # code 6
            result = []
            for tache in self:
                peut_faire = any([i in tache.employee_ids for i in intervenants])
                result.append((tache.id, "%s%s%s" % ('' if peut_faire else '(', tache.name, '' if peut_faire else ')')))
            return result
        return super(OfPlanningTache, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un RDV d'intervention de proposer en priorité les tâches possibles"""
        if self._context.get('intervenant_prio_ids'):
            intervenant_ids = self._context['intervenant_prio_ids'][0][2]  # code 6 [(6, 0, [ids])]
            args = args or []
            res = super(OfPlanningTache, self).name_search(
                name,
                args + [['employee_ids', 'in', intervenant_ids]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(OfPlanningTache, self).name_search(
                name,
                args + [['employee_ids', 'not in', intervenant_ids]],
                operator,
                limit) or []
            return res
        return super(OfPlanningTache, self).name_search(name, args, operator, limit)


class OfPlanningEquipe(models.Model):
    _name = "of.planning.equipe"
    _description = u"Équipe d'intervention"
    _order = "sequence, name"

    @api.model
    def _domain_employee_ids(self):
        return ['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]

    def _default_tz(self):
        return self.env.user.tz or 'Europe/Paris'

    name = fields.Char(u"Équipe", size=128, required=True)
    note = fields.Text("Description")
    employee_ids = fields.Many2many(
        'hr.employee', 'of_planning_employee_rel', 'equipe_id', 'employee_id', u"Employés",
        domain=lambda self: self._domain_employee_ids())
    active = fields.Boolean("Actif", default=True)
    category_ids = fields.Many2many(
        'hr.employee.category', 'equipe_category_rel', 'equipe_id', 'category_id', string=u"Catégories")
    intervention_ids = fields.One2many('of.planning.intervention', 'equipe_id', u"Interventions liées", copy=False)
    tache_ids = fields.Many2many('of.planning.tache', 'equipe_tache_rel', 'equipe_id', 'tache_id', u"Compétences")
    sequence = fields.Integer(u"Séquence", help=u"Ordre d'affichage (plus petit en premier)")
    color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D")
    color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0")
    tz = fields.Selection(
        _tz_get, string="Fuseau horaire", required=True, default=lambda self: self._default_tz(),
        help=u"Le fuseau horaire de l'équipe d'intervention")
    tz_offset = fields.Char(compute='_compute_tz_offset', string="Timezone offset", invisible=True)

    modele_id = fields.Many2one("of.horaire.modele", string=u"Modèle")

    _sql_constraints = [
        ('of_creneau_temp_start_stop_constraint', 'CHECK ( name != NULL )', _(u"contrainte vide")),
        #  @todo: apply_sql supprimer colonne of_creneau_temp_start
    ]

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

    # Domain #

    @api.model
    def _domain_employee_ids(self):
        return ['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]

    # Default #

    @api.model
    def _default_company(self):
        # Pour les objets du planning, le choix de société se fait par un paramètre de config
        if self.env['ir.values'].get_default('of.intervention.settings', 'company_choice') == 'user':
            return self.env['res.company']._company_default_get('of.planning.intervention')
        return False

    @api.model
    def default_get(self, fields_list):
        if 'default_date_prompt' in self._context:
            self = self.with_context(default_date=self._context['default_date_prompt'])
        if 'default_date_deadline_prompt' in self._context:
            self = self.with_context(default_date_deadline=self._context['default_date_deadline_prompt'])
        res = super(OfPlanningIntervention, self).default_get(fields_list)
        res['do_deliveries'] = self.env['ir.values'].get_default('of.intervention.settings', 'do_deliveries')
        return res

    # Champs #

    # Header
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('confirm', "Confirmed"),
            ('done', "Done"),
            ('unfinished', "Unfinished"),
            ('cancel', "Cancelled"),
            ('postponed', "Postponed")], string="State", index=True, readonly=True, default='draft',
        track_visibility='onchange')
    closed = fields.Boolean(string=u"Clôturé", default=False)
    raison_id = fields.Many2one('of.planning.intervention.raison', string="Raison")
    number = fields.Char(String=u"Numéro", copy=False)

    # Rubrique Référence
    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe", oldname='poseur_id')
    employee_ids = fields.Many2many(
        'hr.employee', 'of_employee_intervention_rel', 'intervention_id', 'employee_id',
        string="Intervenants", required=True, domain=lambda self: self._domain_employee_ids())
    employee_main_id = fields.Many2one(
        'hr.employee', string=u"Employé principal", compute="_compute_employee_main_id",
        search="_search_employee_main_id", store=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Client", ondelete='restrict')
    partner_tag_ids = fields.Many2many(comodel_name='res.partner.category', string=u"Étiquettes client",
                                       related='partner_id.category_id', readonly=True)
    address_id = fields.Many2one(comodel_name='res.partner', string=u"Adresse", track_visibility='onchange')
    address_street = fields.Char(related='address_id.street', string=u"Rue", readonly=1)
    address_street2 = fields.Char(related='address_id.street2', string=u"Rue 2", readonly=1)
    address_city = fields.Char(related='address_id.city', string="Ville", oldname="partner_city", readonly=1)
    address_zip = fields.Char(related='address_id.zip', readonly=1)
    address_phone = fields.Char(related='address_id.phone', string=u"Téléphone", readonly=1)
    address_mobile = fields.Char(related='address_id.mobile', string=u"Mobile", readonly=1)
    secteur_id = fields.Many2one(related='address_id.of_secteur_tech_id', readonly=True)
    department_id = fields.Many2one(
        'res.country.department', related='address_id.department_id', string=u"Département", readonly=True, store=True,
        compute_sudo=True)
    user_id = fields.Many2one('res.users', string="Utilisateur", default=lambda self: self.env.uid)
    company_id = fields.Many2one('res.company', string='Magasin', required=True, default=lambda s: s._default_company())
    name = fields.Char(string=u"Libellé", required=True)
    tag_ids = fields.Many2many('of.planning.tag', column1='intervention_id', column2='tag_id', string=u"Étiquettes")

    # Rubrique Planification
    template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template', string=u"Modèle d'intervention", change_default=True)
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche", required=True)
    tache_categ_id = fields.Many2one(related="tache_id.tache_categ_id", readonly=True)
    all_day = fields.Boolean(string=u"Toute la journée")
    forcer_dates = fields.Boolean(
        "Forcer les dates", default=False, help=u"/!\\ outrepasser les horaires des intervenants")
    jour = fields.Char("Jour", compute="_compute_jour")
    date = fields.Datetime(string=u"Date de début", required=True, track_visibility='always')
    date_date = fields.Date(
        string="Jour intervention", compute='_compute_date_date', search='_search_date_date', readonly=True)
    duree = fields.Float(string=u"Durée intervention", required=True, digits=(12, 5), track_visibility='always')
    duree_debut_fin = fields.Float(
        string=u"Durée entre le début et la fin", compute="_compute_duree_debut_fin",
        help=u"Prend en compte le temp de pause au milieu du RDV")
    jour_fin = fields.Char("Jour fin", compute="_compute_jour")
    date_deadline = fields.Datetime(
        compute="_compute_date_deadline", string=u"Date de fin", store=True, track_visibility='always')
    jour_fin_force = fields.Char(u"Jour fin forcé", compute="_compute_jour")
    date_deadline_forcee = fields.Datetime(string=u"Date fin (forcée)")
    # les fonctions de calcul et de recherche des 2 champs suivants sont héritées dans of_mobile
    date_prompt = fields.Datetime(string=u"Date de début", compute="_compute_date_prompt", search="_search_date_prompt")
    date_deadline_prompt = fields.Datetime(
        string=u"Date de fin", compute="_compute_date_deadline_prompt", search="_search_date_deadline_prompt"
    )
    duree_prompt = fields.Float(
        string=u"Durée affichée", compute="_compute_duree_prompt", search="_search_duree_prompt"
    )
    heure_debut_str = fields.Char(string=u"Heure de début", compute="_compute_heure_debut_fin_str")
    heure_fin_str = fields.Char(string=u"Heure de fin", compute="_compute_heure_debut_fin_str")
    horaire_du_jour = fields.Text(string=u"Horaires du jour", compute="_compute_horaire_du_jour")
    verif_dispo = fields.Boolean(
        string=u"Vérif chevauchement", default=True,
        help=u"Vérifier que cette intervention n'en chevauche pas une autre")

    # Rubrique Documents liés
    order_id = fields.Many2one(
        "sale.order", string=u"Commande", copy=False,
        domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")
    order_user_id = fields.Many2one(
        comodel_name='res.users', string=u"Vendeur", related='order_id.user_id', readonly=True)
    order_amount_total = fields.Monetary(string=u"Montant CC", readonly=True, compute='_compute_order_amounts')
    order_still_due = fields.Monetary(string=u"Restant dû CC", readonly=True, compute='_compute_order_amounts')
    picking_amount_total = fields.Monetary(string=u"Montant BL lié", readonly=True, compute='_compute_picking_amounts')

    # Onglet Description
    description = fields.Text(string="Description")
    # old_description = fields.Html(string=u"Ancienne description", readonly=True)
    description_interne = fields.Text(string=u"Description interne")

    # Onglet Notes
    of_notes_intervention = fields.Html(related='order_id.of_notes_intervention', readonly=True)
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)

    # Messages d'alerte
    alert_hors_creneau = fields.Boolean(string=u"RDV hors des créneaux", compute="_compute_date_deadline")
    alert_coherence_date = fields.Boolean(string=u"Incohérence dans les dates", compute="_compute_alert_coherence_date")
    alert_incapable = fields.Boolean(string="Aucun intervenant apte", compute="_compute_alert_incapable")
    alert_wrong_company = fields.Boolean(string=u"Incohérence société", compute='_compute_alert_wrong_company')

    # Pour recherche
    gb_employee_id = fields.Many2one(
        'hr.employee', compute=lambda *a, **k: {}, search='_search_gb_employee_id', string="Intervenant",
        of_custom_groupby=True)

    # Vue Calendar / Planning / Map
    calendar_name = fields.Char(string="Calendar Name", compute="_compute_calendar_name")  # vue Calendar
    tache_name = fields.Char(related='tache_id.name', readonly=True)  # vue Planning
    partner_name = fields.Char(related='partner_id.name')  # vue Planning, vue Map
    partner_phone = fields.Char(related='partner_id.phone')  # vue Map
    partner_mobile = fields.Char(related='partner_id.mobile')  # vue Map
    mobile = fields.Char(related='address_id.mobile')  # vue Planning, of_sms
    phone = fields.Char(related='address_id.phone')  # vue Planning
    tz = fields.Selection(_tz_get, compute='_compute_tz', string="Fuseau horaire")  # vue Calendar
    tz_offset = fields.Char(compute='_compute_tz_offset', string="Timezone offset", invisible=True)  # vue Calendar
    geo_lat = fields.Float(related='address_id.geo_lat', readonly=True)  # vue Map
    geo_lng = fields.Float(related='address_id.geo_lng', readonly=True)  # vue Map
    precision = fields.Selection(related='address_id.precision', readonly=True)  # vue Map
    color_map = fields.Char(compute='_compute_color_map', string=u"Couleur carte")  # vue Map
    of_color_ft = fields.Char(related="employee_main_id.of_color_ft", readonly=True, oldname='color_ft')  # vue Calendar
    of_color_bg = fields.Char(related="employee_main_id.of_color_bg", readonly=True, oldname='color_bg')  # vue Calendar

    # Divers / à classer / inclassable
    category_id = fields.Many2one(related='tache_id.category_id', string=u"Catégorie d'employé")
    # pour faire des stats sur comment sont créés les RDVs
    origin_interface = fields.Char(string=u"Origine création", default=u"Manuelle")
    cleantext_intervention = fields.Text(compute='_compute_cleantext_intervention', store=True, compute_sudo=True)
    interv_before_id = fields.Many2one(
        'of.planning.intervention', compute="_compute_interventions_before_after", store=True, compute_sudo=True)
    interv_after_id = fields.Many2one(
        'of.planning.intervention', compute="_compute_interventions_before_after", store=True, compute_sudo=True)
    before_to_this = fields.Float(compute="_compute_interval", store=True, digits=(12, 5))

    line_ids = fields.One2many('of.planning.intervention.line', 'intervention_id', string='Lignes de facturation')
    lien_commande = fields.Boolean(string='Facturation sur commande', compute='_compute_lien_commande')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale")
    partner_pricelist_id = fields.Many2one(comodel_name='product.pricelist', string=u"Liste de prix",
                                           related='partner_id.property_product_pricelist')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related="company_id.currency_id")

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total HT', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Sous-total TTC', readonly=True, store=True)
    invoice_ids = fields.One2many('account.invoice', string="Factures", compute="_compute_invoice_ids")
    invoice_count = fields.Integer(string="Nombre de factures", compute="_compute_invoice_ids")

    picking_domain = fields.Many2many(comodel_name='stock.picking', compute='_compute_picking_domain')
    picking_manual_ids = fields.Many2many(
        comodel_name='stock.picking', string="Bons de livraison (manuel)",
        domain="order_id and [('id', 'in', picking_domain and picking_domain[0] and picking_domain[0][2] or [])]"
               "or [('picking_type_code', '=', 'outgoing')]",
        relation='of_planning_intervention_picking_manual_rel', column1='intervention_id', column2='picking_id')
    invoice_policy = fields.Selection(
        selection=[
            ('delivery', u'Quantités livrées'),
            ('intervention', u'Quantités planifiées')
        ], string="Politique de facturation", default='intervention', required=True
    )
    invoice_status = fields.Selection(
        selection=[
            ('no', u'Rien à facturer'),
            ('to invoice', u'À facturer'),
            ('invoiced', u'Totalement facturée'),
        ], string=u"État de facturation", compute='_compute_invoice_status', store=True
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', string=u'Entrepôt',
        readonly=True, states={'draft': [('readonly', False), ('required', True)]})
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    picking_ids = fields.One2many(comodel_name='stock.picking', compute="_compute_pickings", string=u"BL associés")
    delivery_count = fields.Integer(string="Nbr Bl", compute="_compute_pickings")
    historique_rdv_ids = fields.One2many(
        comodel_name='of.planning.intervention', compute="_compute_historique_rdv_ids", string="Historique")

    do_deliveries = fields.Boolean(string=u"Utilisation des BL", compute='_compute_do_deliveries')
    flexible = fields.Boolean(string="Flexible")

    # Compute

    @api.multi
    @api.depends('employee_ids')
    def _compute_employee_main_id(self):
        for interv in self:
            if interv.employee_ids:
                interv.employee_main_id = interv.employee_ids[0]

    @api.depends('date', 'date_deadline_forcee', 'date_deadline')
    def _compute_jour(self):
        for interv in self:
            t = ''
            if interv.date:
                dt = datetime.strptime(interv.date, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)  # openerp's ORM method
                t = dt.strftime("%A").capitalize()  # The day_name is Sunday here.
            interv.jour = t
            t_fin = ''
            if interv.date_deadline:
                dt = datetime.strptime(interv.date_deadline, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)  # openerp's ORM method
                t_fin = dt.strftime("%A").capitalize()  # The day_name is Sunday here.
            interv.jour_fin = t_fin
            t_fin_force = ''
            if interv.date_deadline_forcee:
                dt = datetime.strptime(interv.date_deadline_forcee, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)  # openerp's ORM method
                t_fin_force = dt.strftime("%A").capitalize()  # The day_name is Sunday here.
            interv.jour_fin_force = t_fin_force

    @api.depends('date')
    def _compute_date_date(self):
        for interv in self:
            interv.date_date = interv.date

    @api.depends('date', 'date_deadline', 'duree')
    def _compute_duree_debut_fin(self):
        """Ne fonctionne que pour les RDVs sur une seule journée"""
        for intervention in self:
            date_dt = fields.Datetime.from_string(intervention.date)
            date_deadline_dt = fields.Datetime.from_string(intervention.date_deadline)
            # workaround
            if not date_deadline_dt or date_dt.date() != date_deadline_dt.date():
                intervention.duree_debut_fin = intervention.duree
            else:
                intervention.duree_debut_fin = (date_deadline_dt - date_dt).seconds / 3600.0

    @api.depends('date', 'duree', 'employee_ids', 'forcer_dates', 'date_deadline_forcee')
    def _compute_date_deadline(self):
        """Utilise les horaires des employés pour calculer la date de fin de l'intervention"""
        compare_precision = 5
        employee_obj = self.env['hr.employee']
        for interv in self:
            if not (interv.employee_ids and interv.date and interv.duree):
                continue

            if interv.forcer_dates:
                interv.date_deadline = interv.date_deadline_forcee
                interv.alert_hors_creneau = False
            else:
                employees = interv.employee_ids
                tz = pytz.timezone(interv.tz)
                if not tz:
                    tz = "Europe/Paris"

                # Génération courante_da
                date_utc_dt = datetime.strptime(interv.date, "%Y-%m-%d %H:%M:%S")  # Datetime UTC
                date_locale_dt = fields.Datetime.context_timestamp(interv, date_utc_dt)  # Datetime local
                date_locale_str = fields.Datetime.to_string(date_locale_dt).decode('utf-8')  # String Datetime local
                date_courante_da = fields.Date.from_string(date_locale_str)  # Date local
                date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')
                un_jour = timedelta(days=1)
                une_semaine = timedelta(days=7)
                # Pour des raisons pratiques on limite la recherche des horaires
                # à une semaine après la date d'intervention
                date_stop_dt = date_locale_dt + une_semaine
                date_stop_str = fields.Datetime.to_string(date_stop_dt).decode('utf-8')
                # Récupérer le dictionnaire des segments horaires des employés
                horaires_list_dict = employees.get_horaires(date_locale_str, date_stop_str)
                # Récupérer la liste des segments de l'équipe (i.e. l'intersection des horaires des employés)
                segments_equipe = employees.get_horaires_intersection(horaires_list_dict=horaires_list_dict)

                jour_courant = date_locale_dt.isoweekday()

                duree_restante = interv.duree
                # heure en float
                heure_debut = date_locale_dt.hour + (date_locale_dt.minute + date_locale_dt.second / 60.0) / 60.0

                # Vérifier que l'intervention commence sur un créneau travaillé
                index_creneau = employee_obj.debut_sur_creneau(date_courante_str, heure_debut, segments_equipe)
                if index_creneau == -1:
                    interv.alert_hors_creneau = True
                    interv.date_deadline = False
                    continue

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

                    if date_courante_str > segment_courant[1] and len(segments_equipe) > 0:
                        # Changer de segment courant
                        segment_courant = segments_equipe.pop(0)
                        horaires_dict = segment_courant[2]

                    while jour_courant not in horaires_dict or horaires_dict[jour_courant] == []:
                        # On saute les jours non travaillés.
                        jour_courant = ((jour_courant + 1) % 7) or 7  # num jour de la semaine entre 1 et 7
                        date_courante_da += un_jour
                        if date_courante_str > segment_courant[1] and len(segments_equipe) > 0:
                            # Changer de segment courant
                            segment_courant = segments_equipe.pop(0)
                            horaires_dict = segment_courant[2]

                    index_creneau = 0
                    # Heure_courante passée à l'heure de début du premier créneau du jour travaillé suivant
                    heure_courante = horaires_dict[jour_courant][index_creneau][0]

                # La durée restante est égale à 0 ! on y est !
                # String date courante locale
                date_courante_str = fields.Date.to_string(date_courante_da).decode('utf-8')
                # Datetime local début du jour
                date_courante_deb_dt = tz.localize(datetime.strptime(date_courante_str, "%Y-%m-%d"))
                # Calcul de la nouvelle date
                date_deadline_locale_dt = date_courante_deb_dt + timedelta(hours=heure_courante)
                # Avec l'imprécision des durées, il est nécessaire de faire un arrondi à la seconde
                # Les microsecondes seront sinon perdues au formatage en string, plus bas
                # (ça peut provoquer des erreurs)
                date_deadline_locale_dt += timedelta(
                    seconds=date_deadline_locale_dt.microsecond > 500000,
                    microseconds=-date_deadline_locale_dt.microsecond)
                # Conversion en UTC
                date_deadline_utc_dt = date_deadline_locale_dt - date_deadline_locale_dt.tzinfo._utcoffset
                date_deadline_str = date_deadline_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                interv.date_deadline = date_deadline_str
                interv.alert_hors_creneau = False

    @api.depends('date', 'date_deadline')
    def _compute_date_prompt(self):
        for intervention in self:
            intervention.date_prompt = intervention.date

    @api.depends('date_deadline')
    def _compute_date_deadline_prompt(self):
        for intervention in self:
            intervention.date_deadline_prompt = intervention.date_deadline

    @api.depends('duree')
    def _compute_duree_prompt(self):
        for intervention in self:
            intervention.duree_prompt = intervention.duree

    @api.depends('date', 'date_deadline')
    def _compute_heure_debut_fin_str(self):
        for intervention in self:
            # Conversion des dates de début et de fin à l'heure locale
            debut_locale_dt = fields.Datetime.context_timestamp(
                intervention, fields.Datetime.from_string(intervention.date))
            debut_locale_str = fields.Datetime.to_string(debut_locale_dt)
            intervention.heure_debut_str = debut_locale_str[10:16]
            fin_locale_dt = fields.Datetime.context_timestamp(
                intervention, fields.Datetime.from_string(intervention.date_deadline))
            fin_locale_str = fields.Datetime.to_string(fin_locale_dt)
            intervention.heure_fin_str = fin_locale_str[10:16]

    @api.depends('employee_ids', 'date_date')
    def _compute_horaire_du_jour(self):
        for interv in self:
            if interv.employee_ids:
                interv.horaire_du_jour = interv.employee_ids.get_horaires_date(interv.date_date, response_text=True)
            else:
                interv.horaire_du_jour = False

    @api.depends('forcer_dates', 'date_deadline_forcee', 'date', 'duree')
    def _compute_alert_coherence_date(self):
        for interv in self:
            interv.alert_coherence_date = not interv.get_coherence_date_forcee()

    @api.depends('employee_ids', 'tache_id')
    def _compute_alert_incapable(self):
        for interv in self:
            if interv.tache_id and interv.employee_ids \
                    and not interv.employee_ids.peut_faire(interv.tache_id):
                interv.alert_incapable = True
            else:
                interv.alert_incapable = False

    @api.depends('employee_ids', 'company_id')
    def _compute_alert_wrong_company(self):
        for interv in self:
            if interv.company_id and interv.employee_ids.filtered(
                    lambda emp: emp.user_id and interv.company_id not in emp.user_id.company_ids):
                interv.alert_wrong_company = True
            else:
                interv.alert_wrong_company = False

    @api.depends('name', 'number')
    def _compute_calendar_name(self):
        for interv in self:
            interv.calendar_name = interv.number and ' - '.join([interv.number, interv.name]) or interv.name

    @api.depends('employee_ids')
    def _compute_tz(self):
        for interv in self:
            if interv.employee_ids:
                interv.tz = interv.employee_ids[0].of_tz

    @api.depends('tz')
    def _compute_tz_offset(self):
        for interv in self:
            tz = interv.employee_ids and interv.employee_ids[0].of_tz or 'GMT'
            interv.tz_offset = datetime.now(pytz.timezone(tz)).strftime('%z')

    @api.depends('order_id.of_notes_intervention')
    def _compute_cleantext_intervention(self):
        cleanr = re.compile('<.*?>')
        for interv in self:
            cleantext = re.sub(cleanr, '', interv.order_id.of_notes_intervention or '')
            interv.cleantext_intervention = cleantext

    @api.depends('interv_before_id')
    def _compute_interval(self):
        for interv in self:
            if not interv.interv_before_id or not interv.interv_before_id.address_id or not interv.address_id:
                continue
            origine = interv.interv_before_id.address_id
            arrivee = interv.address_id
            routing_base_url = config.get("of_routing_base_url", "")
            routing_version = config.get("of_routing_version", "")
            routing_profile = config.get("of_routing_profile", "")
            if not (routing_base_url and routing_version and routing_profile):
                query = "null"
            else:
                query = routing_base_url + "route/" + routing_version + "/" + routing_profile + "/"

            # Listes de coordonnées : ATTENTION OSRM prend ses coordonnées sous form (lng, lat)
            coords_str = str(origine.geo_lng) + "," + str(origine.geo_lat)
            coords_str += ";" + str(arrivee.geo_lng) + "," + str(arrivee.geo_lat)

            query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
            full_query = query_send + coords_str + "?"
            try:
                req = requests.get(full_query)
                res = req.json()
            except Exception:
                interv.before_to_this = -1.0
                # TODO: Dans certains cas le code ci-dessous provoque une erreur.
                #  On commente donc le code avant de trouver une meilleure solution
                # error = u"\n%s: Impossible de contacter le serveur de routage. (%s)." % (fields.Date.today(), e)
                # interv.sudo().message_post(body=error, subtype_id=self.env.ref('mail.mt_note').id)
                continue

            if res and res.get('routes'):
                interv.before_to_this = (float(res['routes'].pop(0)['duration']) / 60.0) / 60.0

    @api.depends('line_ids', 'line_ids.order_line_id')
    def _compute_lien_commande(self):
        for intervention in self:
            if intervention.line_ids.filtered('order_line_id'):
                intervention.lien_commande = True

    @api.depends('line_ids',
                 'line_ids.price_subtotal',
                 'line_ids.price_tax',
                 'line_ids.price_total',
                 )
    def _compute_amount(self):
        # Calcul repris de la fonction définie pour les bons de commande client dans le module of_sale
        for intervention in self:
            intervention.price_subtotal = sum(intervention.line_ids.mapped('price_subtotal'))
            intervention.price_tax = sum(tax['amount'] for tax in intervention.get_taxes_values().itervalues())
            intervention.price_total = intervention.price_subtotal + intervention.price_tax

    @api.depends('line_ids', 'line_ids.invoice_line_ids', 'order_id', 'order_id.invoice_ids')
    def _compute_invoice_ids(self):
        for rdv in self:
            invoices = rdv.line_ids.sudo().mapped('invoice_line_ids').mapped('invoice_id')
            if rdv.order_id:
                for invoice in rdv.order_id.sudo().invoice_ids:
                    invoices |= invoice
            rdv.invoice_count = len(invoices)
            rdv.invoice_ids = invoices

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

    @api.depends('order_id')
    def _compute_picking_domain(self):
        for intervention in self:
            picking_list = []
            if intervention.order_id:
                picking_list = intervention.order_id.sudo().picking_ids.ids
            intervention.picking_domain = picking_list

    @api.depends('state')
    def _compute_color_map(self):
        u""" COULEURS :
        Gris  : RDV brouillon
        Orange: RDV confirmé
        Rouge : RDV réalisé
        Noir  : autres RDV
        """
        for intervention in self:
            if intervention.state == 'draft':
                intervention.color_map = 'gray'
            elif intervention.state == 'confirm':
                intervention.color_map = 'orange'
            elif intervention.state == 'done':
                intervention.color_map = 'red'
            else:
                intervention.color_map = 'black'

    @api.depends('state', 'line_ids.invoice_status')
    def _compute_invoice_status(self):
        """
        Copie de sale.order._compute_invoice_status(), adaptée pour of.planning.intervention
        Compute the invoice status of a OPI. Possible statuses:
        - no: if the OPF is not in status 'confirm' or 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any OPI line is 'to invoice', the whole OPI is 'to invoice'
        - invoiced: if all OPI lines are invoiced, the OPI is invoiced..
        """
        for rdv in self:
            # Ignore the status of the deposit product
            deposit_product_id = self.env['sale.advance.payment.inv']._default_product_id()
            line_invoice_status = [line.invoice_status for line in rdv.line_ids.filtered(lambda l: not l.order_line_id)
                                   if line.product_id != deposit_product_id]

            if len(line_invoice_status):
                if rdv.state not in ('confirm', 'done'):
                    rdv.invoice_status = 'no'
                elif 'to invoice' in line_invoice_status:
                    rdv.invoice_status = 'to invoice'
                elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                    rdv.invoice_status = 'invoiced'
                else:
                    rdv.invoice_status = 'no'
            else:
                rdv.invoice_status = 'no'

    @api.depends('procurement_group_id')
    def _compute_pickings(self):
        # Faire même calcul que pour les sale.order
        for rdv in self:
            rdv.picking_ids = rdv.procurement_group_id and \
                self.env['stock.picking'].sudo().search([('group_id', '=', rdv.procurement_group_id.id)]) or []
            rdv.delivery_count = len(rdv.picking_ids)

    @api.depends('partner_id', 'address_id')
    def _compute_historique_rdv_ids(self):
        for interv in self:
            if interv.address_id:
                interventions = interv.address_id.intervention_address_ids
            elif interv.partner_id:
                interventions = interv.partner_id.intervention_partner_ids
            else:
                continue
            interv.historique_rdv_ids = interventions.filtered(lambda i: interv.date_date > i.date_date)

    def _compute_do_deliveries(self):
        option = self.env['ir.values'].get_default('of.intervention.settings', 'do_deliveries')
        for rdv in self:
            rdv.do_deliveries = option

    @api.depends('order_id')
    def _compute_order_amounts(self):
        for rdv in self:
            if rdv.order_id:
                # Permet de bypasser le manque de droits sur les commandes et paiements
                # pour avoir l'info du restant dû dans les RDV
                sudo_rdv = rdv.sudo()
                total = sudo_rdv.order_id.amount_total
                if hasattr(sudo_rdv.order_id, 'payment_ids'):
                    still_due = total - sum(sudo_rdv.order_id.payment_ids.mapped('of_amount_total'))
                else:
                    still_due = 0.0
                rdv.order_amount_total = total
                rdv.order_still_due = still_due

    @api.depends('picking_manual_ids')
    def _compute_picking_amounts(self):
        for rdv in self:
            if rdv.picking_manual_ids:
                rdv.picking_amount_total = rdv.picking_manual_ids.sudo().get_sale_value()

    # Search #

    def _search_employee_main_id(self, operator, operand):
        intervs = self.search([])
        res = safe_eval(
            "intervs.filtered(lambda r: r.employee_main_id %s %s)" % (operator, operand), {'intervs': intervs})
        return [('id', 'in', res.ids)]

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

    @api.model
    def _search_date_prompt(self, operator, operand):
        return [('date', operator, operand)]

    @api.model
    def _search_date_deadline_prompt(self, operator, operand):
        return [('date_deadline', operator, operand)]

    @api.model
    def _search_duree_prompt(self, operator, operand):
        return [('duree', operator, operand)]

    def _search_gb_employee_id(self, operator, value):
        return [('employee_ids', operator, value)]

    # Constraints #

    @api.constrains('date_deadline_forcee', 'forcer_dates', 'date', 'duree')
    def check_coherence_date_forcee(self):
        for interv in self:
            if interv.alert_coherence_date:
                if interv.all_day:
                    raise UserError(
                        _(u"Attention /!\\ la durée est trop longue considérant les date de début et de fin"))
                else:
                    raise UserError(
                        _(u"Attention /!\\ la date de fin doit être au moins égale à la date de début + la durée"))

    @api.constrains('date', 'date_deadline')
    def check_alert_hors_creneau(self):
        for interv in self:
            if interv.alert_hors_creneau:
                horaires_du_jour = interv.employee_ids.get_horaires_date(
                    interv.date_date, response_text=True)
                raise UserError(
                    _(u"La date de début des travaux est en dehors des horaires de travail: \n%s") % horaires_du_jour)

    @api.constrains('tache_id', 'employee_ids')
    def check_alert_incapable(self):
        for interv in self:
            if interv.alert_incapable:
                raise UserError(
                    _(u"Aucun des intervenants sélectionnés ne peut réaliser cette tâche"))

    _sql_constraints = [
        ('duree_non_nulle_constraint',
         'CHECK ( duree > 0 )',
         _(u"La durée du RDV d'intervention doit être supérieure à 0!")),
    ]

    # onchange

    @api.onchange('equipe_id')
    def _onchange_equipe_id(self):
        self.ensure_one()
        if self.equipe_id:
            # Affecter les employés
            self.employee_ids = [(5, 0, 0)] + [(4, id_emp, 0) for id_emp in self.equipe_id.employee_ids._ids]

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.ensure_one()
        if self.partner_id:
            self.partner_pricelist_id = self.partner_id.property_product_pricelist
            if not self.address_id:
                addresses = self.partner_id.address_get(['delivery'])
                self.address_id = addresses['delivery']

    @api.onchange('address_id')
    def _onchange_address_id(self):
        name = False
        address = self._context.get('from_portal') and self.address_id.sudo() or self.address_id
        if address:
            if not self.fiscal_position_id:
                self.fiscal_position_id = address.commercial_partner_id.property_account_position_id
            # Pour les objets du planning, le choix de la société se fait par un paramètre de config
            company_choice = self.env['ir.values'].get_default(
                'of.intervention.settings', 'company_choice') or 'contact'
            if company_choice == 'contact' and self.address_id.company_id:
                self.company_id = address.company_id.id
            elif company_choice == 'contact' and self.partner_id and self.partner_id.company_id:
                self.company_id = self.partner_id.company_id.id
            # en mode contact avec un contact sans société, ou en mode user
            else:
                self.company_id = self.env.user.company_id.id
            if not self.partner_id:
                if address.parent_id:
                    address = address.parent_id
                invoice_address_id = address.address_get(['invoice'])['invoice']
                self.partner_id = invoice_address_id
        else:
            self.company_id = self.env.user.company_id.id
        self.onchange_company_id()  # forcer l'appel
        self.name = self.get_name_for_update()

    @api.onchange('template_id')
    def onchange_template_id(self):
        intervention_line_obj = self.env['of.planning.intervention.line']
        template = self.template_id
        template_accounting = template.sudo().with_context(
            force_company=self.company_id.id or self.env.user.company_id.id)
        # context ajouté dans of_service pour initialiser les champs d'un RDV. Utile ici pour prioriser la DI
        if (self.state == "draft" or
                (self.state == 'confirm' and self._context.get('of_intervention_wizard'))) and \
                template and not self._context.get('of_import_service_lines'):
            if template.tache_id and not self._context.get('of_from_contact_form'):
                # We don't want to rechange task if user has changed it manually after the template selection
                # when creating an intervention from a Contact
                self.tache_id = template.tache_id
            # On change la position fiscale par celle du modèle si celle présente n'est pas sur la même société
            # comptable que le RDV ou si il n'y en a pas ET qu'il n'y a pas de lien vers une commande
            change_fiscal_pos = False
            if self.fiscal_position_id:
                comp_accounting_company = getattr(self.company_id, 'accounting_company_id', self.company_id)
                fiscal_accounting_company = getattr(
                    self.fiscal_position_id.company_id, 'accounting_company_id', self.fiscal_position_id.company_id)
                if comp_accounting_company != fiscal_accounting_company:
                    change_fiscal_pos = True
            if template_accounting.fiscal_position_id and not self.lien_commande and \
                    (not self.fiscal_position_id or change_fiscal_pos):
                self.fiscal_position_id = template_accounting.fiscal_position_id
            if not self._context.get('of_intervention_wizard', False) or self._context.get('of_from_contact_form'):
                new_lines = self.line_ids or intervention_line_obj
                for line in template.line_ids:
                    data = line.get_intervention_line_values()
                    data['intervention_id'] = self.id
                    new_lines += intervention_line_obj.new(data)
                new_lines.compute_taxes()
                self.line_ids = new_lines

    @api.onchange('partner_pricelist_id')
    def _onchange_partner_pricelist_id(self):
        if self.partner_pricelist_id:
            for line in self.line_ids:
                product = line.product_id
                line.price_unit = line._get_display_price(product)

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        planning_line_obj = self.env['of.planning.intervention.line']
        if self.tache_id:
            tache_accounting = self.tache_id.sudo().with_context(
                force_company=self.company_id.id or self.env.user.company_id.id)
            if not self.duree and self.tache_id.duree and not self._context.get('of_inhiber_maj_duree'):
                self.duree = self.tache_id.duree
            # On change la position fiscale par celle de la tache si celle présente n'est pas sur la même société
            # comptable que le RDV ou si il n'y en a pas
            change_fiscal_pos = False
            if self.fiscal_position_id:
                comp_accounting_company = getattr(self.company_id, 'accounting_company_id', self.company_id)
                fiscal_accounting_company = getattr(
                    self.fiscal_position_id.company_id, 'accounting_company_id', self.fiscal_position_id.company_id)
                if comp_accounting_company != fiscal_accounting_company:
                    change_fiscal_pos = True
            if tache_accounting.fiscal_position_id and (not self.fiscal_position_id or change_fiscal_pos):
                self.fiscal_position_id = tache_accounting.fiscal_position_id
            # si le contexte contient of_import_service_lines,
            # l'article de la tâche à déjà été ajouté comme ligne de facturation dans la DI.
            # ne pas créer de ligne si la tache a été affecté via le template
            if self.tache_id.product_id and not self._context.get('of_import_service_lines') and \
                    (not self.template_id or self.template_id.tache_id != self.tache_id):
                lines = self.line_ids
                lines |= planning_line_obj.new({
                    'intervention_id': self.id,
                    'product_id': self.tache_id.product_id.id,
                    'qty': 1,
                    'price_unit': self.tache_id.product_id.lst_price,
                    'name': self.tache_id.product_id.name,
                })
                if self.partner_pricelist_id:
                    for line in lines:
                        product = line.product_id
                        line.price_unit = line._get_display_price(product)
                lines.compute_taxes()
                self.line_ids = lines
            self.flexible = self.tache_id.flexible
            # affichage de la description de la tâche
            if self.tache_id.description:
                if self.tache_id.affichage == 'internal_description':
                    description_interne = self.description_interne + "\n" if self.description_interne else ''
                    description_interne += self.tache_id.description
                    self.description_interne = description_interne
                elif self.tache_id.affichage == 'external_description':
                    description = self.description + "\n" if self.description else ''
                    description += self.tache_id.description
                    self.description = description

    @api.onchange('all_day', 'date', 'employee_ids')
    def _onchange_all_day(self):
        u"Pour un RDV sur toute la journée, on ignore les modification d'heure faites par l'utilisateur"
        self.ensure_one()
        if self.all_day and self.employee_ids and self.date:
            update_vals = {'forcer_dates': True}
            tz = pytz.timezone(self.tz or self.env.context.get('tz'))
            # Récupérer l'heure de début de journée et l'affecter
            # passer d'abord la date du RDV en local pour ne pas risquer de récupérer les horaires de la veille
            current_date_utc_dt = pytz.utc.localize(fields.Datetime.from_string(self.date))
            current_date_local_dt = current_date_utc_dt.astimezone(tz)
            current_date_local_str = fields.Date.to_string(current_date_local_dt)
            horaires_du_jour = self.employee_ids.get_horaires_date(current_date_local_str)
            if not any([horaires_du_jour[e] for e in horaires_du_jour]):
                # horaires_du_jour est de la forme { employee1_id : [], employee2_id : [] .. }
                heure_debut_local = self.env['ir.values']\
                                        .get_default('of.intervention.settings', 'calendar_min_time') or 0.0
            else:
                # forcément != 24 car ici au moins un employé a des horaires
                heure_debut_local = min([horaires_du_jour[e] and horaires_du_jour[e][0][0] or 24.0
                                         for e in horaires_du_jour])
            heure_debut_local_str = hours_to_strs('time', heure_debut_local)[0]
            datetime_local_str = '%s %s:00' % (current_date_local_str, heure_debut_local_str)
            datetime_local_dt = tz.localize(datetime.strptime(datetime_local_str, '%Y-%m-%d %H:%M:%S'))
            datetime_utc_dt = datetime_local_dt.astimezone(pytz.utc)
            update_vals['date'] = fields.Datetime.to_string(datetime_utc_dt)
            self.update(update_vals)

    @api.onchange('forcer_dates')
    def _onchange_forcer_dates(self):
        if self.all_day and not self.forcer_dates:
            self.forcer_dates = True
        # lancer le onchange à la main pour initialiser ou mettre à jour la date de fin forcée
        if self.all_day and self.forcer_dates:
            self._onchange_date_deadline_forcee()
        if self.forcer_dates and self.duree and self.date and not self.all_day:
            heures, minutes = float_2_heures_minutes(self.duree)
            self.date_deadline_forcee = fields.Datetime.to_string(
                fields.Datetime.from_string(self.date) + relativedelta(hours=heures, minutes=minutes))

    @api.onchange('date_deadline_forcee', 'employee_ids')
    def _onchange_date_deadline_forcee(self):
        # (re)mettre l'heure de fin à la dernière heure de la journée si RDV sur toute la journée
        if self.forcer_dates and self.all_day and self.employee_ids and (self.date_deadline_forcee or self.date):
            update_vals = {'date_deadline_forcee': self.get_all_day_datetime()}
            self.update(update_vals)

    @api.onchange('order_id')
    def onchange_order_id(self):
        picking_list = []
        if self.order_id:
            picking_list = self.order_id.picking_ids.ids
            self.picking_manual_ids = self.order_id.picking_ids.ids
        else:
            self.picking_manual_ids = False
        self.picking_domain = picking_list
        res = {}
        return res

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            company_id = self.company_id.id
            self.warehouse_id = self.company_id.of_default_warehouse_id
            # La société a changé, si elle ne correspond pas à la position fiscale, on modifie cette dernière
            change_fiscal_pos = False
            if self.fiscal_position_id:
                comp_accounting_company = getattr(self.company_id, 'accounting_company_id', self.company_id)
                fiscal_accounting_company = getattr(
                    self.fiscal_position_id.company_id, 'accounting_company_id', self.fiscal_position_id.company_id)
                if comp_accounting_company != fiscal_accounting_company:
                    change_fiscal_pos = True
            if change_fiscal_pos or not self.fiscal_position_id:
                template_accounting = self.template_id.sudo().with_context(force_company=company_id)
                tache_accounting = self.tache_id.sudo().with_context(force_company=company_id)
                if template_accounting.fiscal_position_id:
                    self.fiscal_position_id = template_accounting.fiscal_position_id
                elif tache_accounting.fiscal_position_id:
                    self.fiscal_position_id = tache_accounting.fiscal_position_id
                elif self.fiscal_position_id:
                    self.fiscal_position_id = False

    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id(self):
        """
        Modification des taxes affectées aux ligne de l'intervention lors du changement de position fiscale.
        Exceptions pour les lignes déjà facturées ou liées à une commande, celles-ci doivent concerver leurs taxes.
        """
        if self.fiscal_position_id:
            self.line_ids.filtered(lambda l: not l.sudo().order_line_id and not l.sudo().invoice_line_ids).\
                _compute_tax_id()

    # Héritages

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
    def create(self, vals):
        if 'default_date' in self._context:
            # On doit supprimer 'default_date' du context, sans quoi il affecte la creation des mail.message
            if 'date' not in vals:
                vals['date'] = self._context['default_date']
            new_context = dict(self._context)
            del new_context['default_date']
            self = self.with_context(new_context)
        if 'date' in vals:
            # Tronqué à la minute
            vals['date'] = vals['date'][:17] + '00'
        res = super(OfPlanningIntervention, self).create(vals)
        res.do_verif_dispo()
        res._affect_number()

        # Si BL associé, on met à jour la date du BL en fonction de la date d'intervention
        if 'picking_manual_ids' in vals and 'date' in vals:
            if res.picking_manual_ids:
                res.picking_manual_ids.write({'min_date': res.date})

        if res.employee_ids:
            res.message_post(body=_(u"Intervenants: %s") % ', '.join(res.employee_ids.mapped('name')))

        return res

    @api.multi
    def write(self, vals):
        ri_report = self.env.ref('of_planning.of_planning_raport_intervention_report', raise_if_not_found=False)
        default_template = self.env.ref(
            'of_planning.of_planning_default_intervention_template', raise_if_not_found=False)
        if 'default_date' in self._context:
            # On doit supprimer 'default_date' du context, sans quoi il affecte la creation des mail.message
            new_context = dict(self._context)
            del new_context['default_date']
            self = self.with_context(new_context)
        if 'date' in vals:
            # Tronqué à la minute
            vals['date'] = vals['date'][:17] + '00'
        # Correspond soit au drag & drop soit au redimensionnage
        # -> affecter la date de fin forcée pour les RDVs sur toute la journée
        # -> ignorer les horaires de travail et les interventions superposées pour les autres RDVs
        if self._context.get('from_ui'):
            vals['verif_dispo'] = False
            vals['forcer_dates'] = True
            vals['date'] = vals.get('date', vals.get('date_prompt', False))
            all_day = vals.get('all_day') if 'all_day' in vals else self.all_day
            vals['date_deadline'] = vals.get('date_deadline', vals.get('date_deadline_prompt', False))
            if all_day:
                # de la forme [[6, 0, ids_list]] en cas de drag n drop
                employee_eval = vals.get('employee_ids', [[-1, 0, []]])[0][2]
                vals['date'], vals['date_deadline_forcee'] = self.get_all_day_datetime(
                    mode='both', date_eval=vals['date'], employee_eval=employee_eval)
            elif vals.get('date_deadline'):
                vals['date_deadline_forcee'] = vals['date_deadline'][:17] + '00'

            if vals.get('date_deadline_forcee'):
                date_deadline_dt = fields.Datetime.from_string(vals['date_deadline_forcee'])
                del vals['date_deadline']
                # date et date_deadline modifiées -> drag n drop
                if vals.get('date'):
                    date_dt = fields.Datetime.from_string(vals.get('date'))
                # seulement date_deadline modifiée -> redimensionnage
                else:
                    # len(self) == 1 car drag n drop ou redimensionnage
                    date_dt = fields.Datetime.from_string(self[0].date)
                vals['duree'] = (date_deadline_dt - date_dt).total_seconds() / 3600
        employee_before = {rec: rec.employee_ids for rec in self}

        result = super(OfPlanningIntervention, self).write(vals)
        if vals.get('state', '') == 'confirm':
            self.mapped('line_ids').sudo()._action_procurement_create()

        # Génération auto du rapport d'intervention
        if ri_report and vals.get('state', '') == 'done':
            for record in self:
                if (record.template_id and record.template_id.attach_report) or (
                        default_template and default_template.attach_report):
                    self.env['report'].sudo().get_pdf(docids=record._ids, report_name=ri_report.report_name)
        # Validation auto des BL si l'intervention est passée à l'état "Réalisé"
        if vals.get('state') == 'done':
            for picking in self.sudo().mapped('picking_ids').filtered(
                    lambda p: p.state in ('partially_available', 'assigned')):
                self.env['stock.immediate.transfer'].create({'pick_id': picking.id}).process()

        self._affect_number()
        if vals.get('state', '') == 'done':
            self._send_report()

        # Si BL associés, on met à jour la date des BL en fonction de la date d'intervention
        if 'picking_manual_ids' in vals or 'date' in vals:
            for rdv in self:
                if rdv.picking_manual_ids:
                    rdv.picking_manual_ids.write({'min_date': rdv.date})

        if 'employee_ids' in vals:
            for rdv in self:
                rdv.message_post(body=_(u"Intervenants: %s => %s") % (
                    ', '.join(employee_before[rdv].mapped('name')),
                    ', '.join(rdv.employee_ids.mapped('name'))
                ))

        return result

    @api.multi
    def _write(self, vals):
        res = super(OfPlanningIntervention, self)._write(vals)
        if vals.get('employee_ids') or vals.get('date') or vals.get('date_deadline') or vals.get('verif_dispo'):
            self.do_verif_dispo()
        return res

    @api.multi
    def unlink(self):
        pickings = self.mapped('picking_ids')
        res = super(OfPlanningIntervention, self).unlink()
        pickings.filtered(lambda p: p.state != 'done').unlink()
        return res

    def copy(self, default=None):
        interv_new = super(OfPlanningIntervention, self).copy(default=default)
        for line in self.line_ids:
            line.copy({'intervention_id': interv_new.id})
        return interv_new

    @api.multi
    def copy_data(self, default=None):
        default = default.copy() if default else {}
        default['verif_dispo'] = False
        default['origin_interface'] = 'duplication manuelle'
        return super(OfPlanningIntervention, self).copy_data(default)

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'gb_employee_id':
            return super(OfPlanningIntervention, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'of_employee_intervention_rel', 'id', 'intervention_id', 'employee_ids'),
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

    # Actions

    @api.multi
    def create_invoice(self):
        invoice_obj = self.env['account.invoice']

        msgs = []
        for interv in self:
            # toutes les lignes sont liées à une commande (au moins une avec commande et aucune sans commande)
            if interv.lien_commande and not interv.line_ids.filtered(lambda l: not l.order_line_id):
                msgs.append(u"Les lignes facturables du rendez-vous %s étant liées à des lignes de commandes "
                            u"veuillez effectuer la facturation depuis le bon de commande." % interv.name)
                continue
            invoice_data, msg = interv._prepare_invoice()
            msgs.append(msg)
            if invoice_data:
                invoice = invoice_obj.create(invoice_data)
                invoice.compute_taxes()
                invoice.message_post_with_view('mail.message_origin_link',
                                               values={'self': invoice, 'origin': interv},
                                               subtype_id=self.env.ref('mail.mt_note').id)
        msg = "\n".join(msgs)

        return {
            'name': u"Création de la facture",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.planning.message.invoice',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_msg': msg}
        }

    @api.multi
    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.multi
    def action_intervention_send(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'of.planning.intervention',
            'default_res_id': self.ids[0],
            'default_composition_mode': 'comment',
            'force_attachment': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def button_confirm(self):
        self.write({'state': 'confirm'})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_done(self):
        self.write({'state': 'done'})
        for picking in self.mapped('picking_ids').filtered(lambda p: p.state in ('partially_available', 'assigned')):
            self.env['stock.immediate.transfer'].create({'pick_id': picking.id}).process()
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_unfinished(self):
        self.write({'state': 'unfinished'})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_postponed(self):
        self.write({'state': 'postponed'})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancel'})
        if self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')).action_cancel()
        self.mapped('line_ids').mapped('procurement_ids').cancel()  # la fonctionne n'annule pas les appro déjà terminés
        self.mapped('line_ids').mapped('procurement_ids').filtered(lambda p: p.state == 'cancel')\
            .write({'of_intervention_line_id': False})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_draft(self):
        self.write({'state': 'draft'})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_close(self):
        self.write({'closed': True})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_open(self):
        self.write({'closed': False})
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_import_order_line(self):
        self.ensure_one()
        line_obj = self.env['of.planning.intervention.line']
        if not self.order_id:
            raise UserError(u"Il n'y a pas de commande liée a l'intervention.")
        self.fiscal_position_id = self.order_id.fiscal_position_id
        in_use = self.line_ids.mapped('order_line_id')._ids
        for line in self.order_id.order_line.filtered(lambda l: l.id not in in_use):
            qty = line.product_uom_qty - sum(
                line.of_intervention_line_ids
                .filtered(lambda r: r.intervention_id.state not in ('cancel', 'postponed'))
                .mapped('qty'))
            if qty > 0.0:
                line_obj.create({
                    'order_line_id': line.id,
                    'intervention_id': self.id,
                    'product_id': line.product_id.id,
                    'qty': qty,
                    'price_unit': line.price_unit,
                    'name': line.name,
                    'taxe_ids': [(4, tax.id) for tax in line.tax_id]
                })
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_update_lines(self):
        self.ensure_one()
        self.line_ids.update_vals()
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def action_view_delivery(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    # Autres

    @api.multi
    def get_taxes_values(self):
        self.ensure_one()
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.taxe_ids.compute_all(
                price_unit, self.currency_id, line.qty,
                product=line.product_id, partner=self.address_id)['taxes']
            for val in taxes:
                key = val['account_id']

                val['amount'] += val['base'] - round_curr(val['base'])
                if key not in tax_grouped:
                    tax_grouped[key] = {
                        'tax_id': val['id'],
                        'amount': val['amount'],
                        'base': round_curr(val['base'])
                    }
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])

        for values in tax_grouped.itervalues():
            values['base'] = round_curr(values['base'])
            values['amount'] = round_curr(values['amount'])
        return tax_grouped

    @api.multi
    def get_interv_prec_suiv(self, employee_id):
        """Renvoie l'intervention précédente à celle-ci pour l'employé donné
        (différent potentiellement de interv_before_id pour les interventions à plusieurs employés)"""
        if not self:
            return False, False
        self.ensure_one()
        if not employee_id:
            employee_id = self.employee_ids and self.employee_ids[0].id
        interv_obj = self.env['of.planning.intervention']
        interv_prec = interv_obj.search(
            [
                ('date_date', '=', self.date_date),
                ('date', '<', self.date),  # strict pour ne pas récupérer l'intervention du self
                ('employee_ids', 'in', employee_id)
            ], order="date DESC", limit=1)
        interv_suiv = interv_obj.search(
            [
                ('date_date', '=', self.date_date),
                ('date', '>', self.date),  # strict pour ne pas récupérer l'intervention du self
                ('employee_ids', 'in', employee_id)
            ], order="date DESC", limit=1)
        return interv_prec or False, interv_suiv or False

    @api.multi
    def of_get_report_name(self, docs):
        if self._context.get('of_report_name'):
            return self._context.get('of_report_name')
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
        return v0, v1, v2, v3

    @api.multi
    def get_coherence_date_forcee(self):
        """
        :return: False si dates forcées et incohérence. True sinon
        """
        self.ensure_one()
        if self.date_deadline_forcee and self.forcer_dates and self.date and self.duree:
            diff_heures = (fields.Datetime.from_string(self.date_deadline_forcee)
                           - fields.Datetime.from_string(self.date))
            # on convertit la durée pour faciliter la comparaison
            heures, minutes = float_2_heures_minutes(self.duree)
            duree_td = timedelta(hours=heures, minutes=minutes)
            # éviter les erreurs d'arrondi de minute
            une_minute = timedelta(minutes=1)
            ecart = duree_td - diff_heures
            if une_minute < ecart:
                return False
        return True

    def get_all_day_datetime(self, mode='end', date_eval=False, employee_eval=[]):
        u"""
        Renvois le datetime string de début/fin de journée pour un RDV sur toute la journée
        :param mode: 'end', 'start' ou 'both'. Tout autre valeur compte comme 'both'
        :param date_eval: date à évaluer, si différente de celle du RDV
        :param employee_eval: liste d'employés à évaluer, si différente de celle du RDV
        :return: suivant le mode, le datetime de début, de fin, ou les 2 dans un tuple
        """
        self.ensure_one()
        tz = pytz.timezone(self.tz or self.env.context.get('tz'))
        # Récupérer l'heure de fin de journée et l'affecter
        # passer d'abord la date de fin du RDV en local pour ne pas risquer de récupérer les horaires du lendemain
        date_used = date_eval or self.date_deadline_forcee or self.date
        current_date_utc_dt = pytz.utc.localize(fields.Datetime.from_string(date_used))
        current_date_local_dt = current_date_utc_dt.astimezone(tz)
        current_date_local_str = fields.Date.to_string(current_date_local_dt)
        employee_used = self.env['hr.employee'].browse(employee_eval) or self.employee_ids
        horaires_du_jour = employee_used.get_horaires_date(current_date_local_str)
        # si mode vaut 'start' ou 'both', on calcul le datetime de début de journée
        if mode != 'end':
            if not any([horaires_du_jour[e] for e in horaires_du_jour]):
                # horaires_du_jour est de la forme { employee1_id : [], employee2_id : [] .. }
                heure_debut_local = self.env['ir.values'] \
                                        .get_default('of.intervention.settings', 'calendar_min_time') or 0.0
            else:
                # forcément != 0 car ici au moins un employé a des horaires
                heure_debut_local = min([horaires_du_jour[e] and horaires_du_jour[e][0][0] or 24.0
                                         for e in horaires_du_jour])
            heure_debut_local_str = hours_to_strs('time', heure_debut_local)[0]
            datetime_deb_local_str = '%s %s:00' % (current_date_local_str, heure_debut_local_str)
            datetime_deb_local_dt = tz.localize(datetime.strptime(datetime_deb_local_str, '%Y-%m-%d %H:%M:%S'))
            datetime_deb_utc_dt = datetime_deb_local_dt.astimezone(pytz.utc)
            datetime_deb_utc_str = fields.Datetime.to_string(datetime_deb_utc_dt)
            if mode == 'start':
                return datetime_deb_utc_str
        # ici mode vaut 'end' ou 'both', on calcule le datetime de fin de journée
        if not any([horaires_du_jour[e] for e in horaires_du_jour]):
            # horaires_du_jour est de la forme { employee1_id : [], employee2_id : [] .. }
            heure_fin_local = self.env['ir.values'] \
                                  .get_default('of.intervention.settings', 'calendar_max_time') or 24.0
        else:
            # forcément != 0 car ici au moins un employé a des horaires
            heure_fin_local = max([horaires_du_jour[e] and horaires_du_jour[e][-1][-1] or 0.0
                                   for e in horaires_du_jour])
        # 00:00 du jour suivant, on met plutôt 23:59 pour rester le même jour et éviter les problèmes
        if heure_fin_local == 24.0:
            heure_fin_local_str = '23:59'
        else:
            heure_fin_local_str = hours_to_strs('time', heure_fin_local)[0]
        datetime_fin_local_str = '%s %s:00' % (current_date_local_str, heure_fin_local_str)
        datetime_fin_local_dt = tz.localize(datetime.strptime(datetime_fin_local_str, '%Y-%m-%d %H:%M:%S'))
        datetime_fin_utc_dt = datetime_fin_local_dt.astimezone(pytz.utc)
        datetime_fin_utc_str = fields.Datetime.to_string(datetime_fin_utc_dt)
        if mode == 'end':
            return datetime_fin_utc_str
        return (datetime_deb_utc_str, datetime_fin_utc_str)

    def _get_domain_states_values_overlap(self):
        return ['cancel', 'postponed']

    def _get_domain_do_check_overlap(self, interv, date_prompt=False):
        if date_prompt:
            return [
                # /!\ conserver .ids : ._ids est un tuple et génère une erreur à l'évaluation
                ('employee_ids', 'in', interv.employee_ids.ids),
                ('date_prompt', '<', interv.date_deadline),
                ('date_deadline_prompt', '>', interv.date),
                ('id', '!=', interv.id),
                ('state', 'not in', self._get_domain_states_values_overlap()),
            ]
        return [
            # /!\ conserver .ids : ._ids est un tuple et génère une erreur à l'évaluation
            ('employee_ids', 'in', interv.employee_ids.ids),
            ('date', '<', interv.date_deadline),
            ('date_deadline', '>', interv.date),
            ('id', '!=', interv.id),
            ('state', 'not in', self._get_domain_states_values_overlap()),
        ]

    @api.multi
    def do_verif_dispo(self):
        # Vérification de la validité du créneau: chevauchement
        interv_obj = self.env['of.planning.intervention'].with_context(virtual_id=True)
        group_flex = self.env.user.has_group('of_planning.of_group_planning_intervention_flexibility')
        for interv in self:
            if group_flex and interv.flexible:
                continue
            if interv.verif_dispo:
                domain = self._get_domain_do_check_overlap(interv, date_prompt=True)
                if group_flex:
                    domain += [('flexible', '=', False)]
                rdv = interv_obj.search(domain, limit=1)
                if rdv:
                    lang = self.env['res.lang']._lang_get(self.env.user.lang)
                    date = fields.Datetime.context_timestamp(rdv, fields.Datetime.from_string(rdv.date))
                    date_d = fields.Datetime.context_timestamp(rdv, fields.Datetime.from_string(rdv.date_deadline))
                    date_start = date.strftime(lang.date_format + " " + lang.time_format)
                    date_stop = date_d.strftime(lang.time_format)
                    if date.date() != date_d.date():
                        date_stop = date_d.strftime(lang.date_format) + " " + date_stop
                    raise ValidationError(
                        u"L'employé %s a déjà au moins un rendez-vous sur ce créneau.\n"
                        u"Rdv : %s - %s : %s\n"
                        u"(id du rdv: %s)" %
                        ((rdv.employee_ids & interv.employee_ids)[0].name,
                         date_start, date_stop, rdv.name,
                         rdv.id))

    @api.multi
    def get_overlapping_intervention(self):
        # Vérification de la validité du créneau: chevauchement
        interv_obj = self.env['of.planning.intervention'].with_context(virtual_id=True)
        rdvs = interv_obj
        for interv in self:
            if interv.verif_dispo:
                domain = self._get_domain_do_check_overlap(interv, date_prompt=False)
                rdv = interv_obj.search(domain, limit=1)
                if rdv:
                    rdvs |= rdv
        return rdvs

    @api.multi
    def _affect_number(self):
        for interv in self:
            if interv.template_id\
                    and interv.state in ('confirm', 'done', 'unfinished', 'postponed')\
                    and not interv.number:
                interv.write({'number': self.template_id.sequence_id.next_by_id()})

    @api.multi
    def _send_report(self):
        ir_model_data = self.env['ir.model.data']
        default_template = self.env.ref('of_planning.of_planning_default_intervention_template',
                                        raise_if_not_found=False)
        for interv in self:
            if interv.state == 'done' and (interv.template_id and interv.template_id.send_reports == 'auto_done'
                                           or not interv.template_id and default_template
                                           and default_template.send_reports == 'auto_done'):
                try:
                    mail_template = ir_model_data.get_object(
                        'of_planning', 'email_template_of_planning_intervention_rapport_intervention')
                except ValueError:
                    raise UserError(u"Le modèle pour l'envoi du rapport d'intervention n'existe pas. "
                                    u"Veuillez contacter le support.")
                mail_template.send_mail(interv.id, force_send=True)

    @api.multi
    def _get_invoicing_company(self, partner):
        return self.company_id or partner.company_id

    @api.multi
    def _prepare_invoice_lines(self):
        self.ensure_one()
        lines_data = []
        error = ''
        for line in self.line_ids.filtered(lambda l: l.invoice_status == 'to invoice' and not l.order_line_id):
            line_data, line_error = line._prepare_invoice_line()
            lines_data.append((0, 0, line_data))
            error += line_error
        return lines_data, error

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()

        msg_succes = u"SUCCÈS : création de la facture depuis l'intervention %s"
        msg_erreur = u"ÉCHEC : création de la facture depuis l'intervention %s : %s"

        partner = self.partner_id
        if not partner:
            if self.address_id:
                if self.address_id.parent_id:
                    invoice_address_id = self.address_id.parent_id.address_get(['invoice'])['invoice']
                else:
                    invoice_address_id = self.address_id.address_get(['invoice'])['invoice']
                partner = self.env['res.partner'].browse(invoice_address_id)
            else:
                return (False,
                        msg_erreur % (self.name, u'Pas de partenaire défini'))
        pricelist = partner.property_product_pricelist
        lines_data, error = self._prepare_invoice_lines()
        if error:
            return (False,
                    msg_erreur % (self.name, error))
        if not lines_data:
            return (False,
                    msg_erreur % (self.name, u"Aucune ligne facturable."))
        company = self._get_invoicing_company(partner)
        fiscal_position_id = self.fiscal_position_id.id or partner.property_account_position_id.id

        journal_id = (self.env['account.invoice'].with_context(company_id=company.id)
                      .default_get(['journal_id'])['journal_id'])
        if not journal_id:
            return (False,
                    msg_erreur % (
                        self.name,
                        u"Vous devez définir un journal des ventes pour cette société (%s)." % company.name))
        invoice_data = {
            'origin': self.number or 'Intervention',
            'type': 'out_invoice',
            'account_id': partner.property_account_receivable_id.id,
            'partner_id': partner.id,
            'partner_shipping_id': self.address_id.id,
            'journal_id': journal_id,
            'currency_id': pricelist.currency_id.id,
            'fiscal_position_id': fiscal_position_id,
            'company_id': company.id,
            'user_id': self._uid,
            'invoice_line_ids': lines_data,
        }

        return (invoice_data,
                msg_succes % (self.name,))

    @api.model
    def get_color_filter_data(self):
        res = {}
        default_filter = self.env['ir.values'].get_default('of.intervention.settings',
                                                           'of_event_color_filter',
                                                           for_all_users=False)
        res['intervenant'] = {
            'is_checked': not default_filter or default_filter == u'intervenant',
            'label': u'Intervenant',
            'field': u'employee_ids',
            'color_ft_field': u'of_color_ft',
            'color_bg_field': u'of_color_bg',
            'catpions': False,
        }
        res['tache_categ'] = {
            'is_checked': default_filter == u'tache_categ',
            'label': u'Catégorie de tâche',
            'field': u'tache_categ_id',
            'color_ft_field': u'color_ft',
            'color_bg_field': u'color_bg',
            'captions': self.env['of.planning.tache.categ'].get_caption_data(),
        }

        return res

    @api.model
    def get_color_map(self):
        u"""
        Fonction pour la légende de la vue map
        """
        title = "Interventions"
        v0 = {'label': u"Brouillon", 'value': 'gray'}
        v1 = {'label': u"Confirmé", 'value': 'orange'}
        v2 = {'label': u"Réalisé", 'value': 'red'}
        v3 = {'label': u"Autre", 'value': 'black'}
        return {"title": title, "values": (v0, v1, v2, v3)}

    def _prepare_procurement_group(self):
        return {'name': self.name, 'partner_id': self.address_id.id}

    @api.multi
    def picking_lines_layouted(self):
        self.ensure_one()
        layouted = []
        pickings = self.picking_manual_ids
        for picking in pickings:
            layouted.append({'name': picking.name, 'lines': picking.move_lines})
        return layouted

    @api.model
    def _allowed_reports_template(self):
        """
        Fonction qui affecte un nom de rapport à un modèle.
        Si le nom de rapport imprimé n'est pas dans la liste de clés du dictionnaire,
        alors les documents joints ne seront pas imprimés.
        :return: {'nom_du_rapport' : modèle.concerné'}
        """
        return ['of_planning.of_planning_fiche2_intervention_report_big_template',
                'of_planning.of_planning_rapport_intervention_report_template']

    @api.multi
    def _detect_doc_joint_template(self, report_name):
        """
        Cette fonction retourne les données des documents à joindre au fichier pdf du devis/commande au format binaire.
        Le document retourné correspond au fichier pdf joint au modéle de courrier.
        @todo: Permettre l'utilisation de courriers classiques et le remplissage des champs.
        :return: liste des documents à ajouter à la suite du rapport
        """
        template = self.template_id or self.env.ref('of_planning.of_planning_default_intervention_template',
                                                    raise_if_not_found=False)
        if template and report_name == 'of_planning.of_planning_fiche2_intervention_report_big_template':
            return template.fi_doc_joints(self)
        if template and report_name == 'of_planning.of_planning_rapport_intervention_report_template':
            return template.ri_doc_joints(self)
        return []

    @api.multi
    def get_action_views(self, obj_source, action):
        interv_count = len(self)
        if interv_count >= 1:
            # changer l'ordre des vues de l'action est suffisant pour mettre la vue tree en première
            views = [(self.env['ir.model.data'].xmlid_to_res_id(
                'of_planning.of_planning_intervention_view_tree'), 'tree')]
            views += [(view[0], view[1]) for view in action['views'] if view[1] != 'tree']
            action['views'] = views
        return action

    @api.multi
    def pickings_layouted(self):
        pickings_layouted = []
        pickings = self.mapped('picking_manual_ids') + self.mapped('picking_ids')
        for picking in pickings:
            if picking.pack_operation_product_ids:
                pickings_layouted.append({
                    'name': picking.name,
                    'lines': picking.pack_operation_product_ids,
                })
        return pickings_layouted

    def get_name_for_update(self):
        u"""This function is inherited in of_planning_google"""
        self.ensure_one()
        name = u""
        address = self._context.get('from_portal') and self.address_id.sudo() or self.address_id
        if address:
            name = [address.name_get()[0][1]]
            for field in ('zip', 'city'):
                val = getattr(self.address_id, field)
                if val:
                    name.append(val)
        name = name and " ".join(name) or "Intervention"
        return name

    @api.multi
    def action_move_intervention_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': u"Éditions des interventions",
            'res_model': 'of.move.rdv.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_intervention_ids': self._ids}
        }


class OfPlanningInterventionLine(models.Model):
    _name = "of.planning.intervention.line"

    intervention_id = fields.Many2one(
        'of.planning.intervention', string='Intervention', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='intervention_id.partner_id', readonly=True)
    company_id = fields.Many2one('res.company', related='intervention_id.company_id', string=u'Société', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related="company_id.currency_id")

    order_line_id = fields.Many2one('sale.order.line', string='Ligne de commande', copy=False)
    so_number = fields.Char(
        string=u"Numéro de commande client", related='order_line_id.order_id.name', readonly=True)
    product_id = fields.Many2one('product.product', string='Article')
    price_unit = fields.Monetary(
        string='Prix unitaire', digits=dp.get_precision('Product Price'), default=0.0, currency_field='currency_id'
    )
    qty = fields.Float(string=u'Qté', digits=dp.get_precision('Product Unit of Measure'))
    name = fields.Text(string='Description')
    taxe_ids = fields.Many2many('account.tax', string="TVA")
    discount = fields.Float(string='Remise (%)', digits=dp.get_precision('Discount'), default=0.0)
    qty_delivered = fields.Float(string=u"Qté livrée", copy=False)
    qty_invoiced = fields.Float(string=u"Qté facturée", compute='_compute_qty_invoiced', store=True)
    qty_invoiceable = fields.Float(string=u"Qté a facturer", compute='_compute_qty_invoiceable', store=True)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total HT', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Sous-total TTC', readonly=True, store=True)

    intervention_state = fields.Selection(related="intervention_id.state", store=True)
    invoice_line_ids = fields.One2many(
        'account.invoice.line', 'of_intervention_line_id', string=u"Ligne de facturation")
    procurement_ids = fields.One2many('procurement.order', 'of_intervention_line_id', string='Procurements')
    invoice_policy = fields.Selection(related="intervention_id.invoice_policy", string="Politique de facturation")
    invoice_status = fields.Selection(selection=[
        ('no', u'Rien à facturer'),
        ('to invoice', u'À facturer'),
        ('invoiced', u'Totalement facturée'),
    ], string=u"État de facturation", compute='_compute_invoice_status', store=True
    )

    @api.depends('qty', 'price_unit', 'taxe_ids')
    def _compute_amount(self):
        """
        Calcule le montant de la ligne.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxe_ids.compute_all(price, line.currency_id, line.qty,
                                              product=line.product_id, partner=line.intervention_id.address_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('product_id')
    def _onchange_product(self):
        product = self.product_id
        self.qty = 1
        if self.intervention_id.partner_id and self.intervention_id.partner_pricelist_id:
            self.price_unit = self._get_display_price(product)
        else:
            self.price_unit = product.lst_price
        if product:
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
        else:
            self.name = ''
        if product:
            self.compute_taxes()

    @api.multi
    def _get_display_price(self, product):
        return product.with_context(pricelist=self.intervention_id.partner_pricelist_id.id).price

    @api.multi
    def compute_taxes(self):
        for line in self:
            product = line.product_id
            partner = line.partner_id
            fiscal_position = line.intervention_id.fiscal_position_id
            taxes = product.taxes_id
            if taxes:
                company = line.intervention_id._get_invoicing_company(partner)
                if 'accounting_company_id' in company._fields:
                    company = company.accounting_company_id
                taxes = taxes.filtered(lambda r: r.company_id == company)
            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes, product, partner)
            line.taxe_ids = taxes

    @api.depends('invoice_line_ids', 'invoice_line_ids.invoice_id', 'invoice_line_ids.quantity')
    def _compute_qty_invoiced(self):
        for line in self:
            line.qty_invoiced = sum(line.sudo().invoice_line_ids.mapped('quantity'))

    @api.depends('intervention_id.invoice_policy', 'intervention_id.state',
                 'qty', 'qty_delivered', 'qty_invoiced', 'order_line_id')
    def _compute_qty_invoiceable(self):
        for line in self:
            if line.intervention_id.state not in ('confirm', 'done') or line.order_line_id:
                line.qty_invoiceable = 0.0
            elif line.invoice_policy == 'intervention':
                line.qty_invoiceable = line.qty - line.qty_invoiced
            elif self.invoice_policy == 'delivered':
                line.qty_invoiceable = line.qty_delivered - line.qty_invoiced

    @api.depends('intervention_id.state', 'qty', 'qty_delivered', 'qty_invoiced', 'order_line_id', 'qty_invoiceable')
    def _compute_invoice_status(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.intervention_id.state not in ('confirm', 'done') or line.order_line_id:
                line.invoice_status = 'no'
            elif not float_is_zero(line.qty_invoiceable, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif float_compare(line.qty_invoiced, line.qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.intervention_id.fiscal_position_id
            taxes = line.company_id._of_filter_taxes(line.product_id.taxes_id)
            line.taxe_ids = fpos and fpos.map_tax(taxes, line.product_id, line.intervention_id.address_id) or taxes

    @api.model
    def create(self, vals):
        res = super(OfPlanningInterventionLine, self).create(vals)
        if res.intervention_id.state == 'confirm':
            res.sudo()._action_procurement_create()
        return res

    @api.multi
    def write(self, vals):
        res = super(OfPlanningInterventionLine, self).write(vals)
        if 'qty' in vals:
            self.sudo()._action_procurement_create()
        return res

    @api.multi
    def _prepare_invoice_line(self):
        self.ensure_one()
        product = self.product_id
        partner = self.partner_id
        if not self.intervention_id.fiscal_position_id:
            return {}, u"Veuillez définir une position fiscale pour l'intervention %s" % self.name
        fiscal_position = self.intervention_id.fiscal_position_id
        taxes = self.taxe_ids
        if taxes:
            company = self.intervention_id._get_invoicing_company(partner)
            if company:
                if 'accounting_company_id' in company._fields:
                    company = company.accounting_company_id
                taxes = taxes.filtered(lambda r: r.company_id == company)
        elif fiscal_position:
            taxes = fiscal_position.map_tax(taxes, product, partner)

        line_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not line_account:
            return {}, u'Il faut configurer les comptes de revenus pour la catégorie du produit %s.\n' % product.name

        # Mapping des comptes par taxe induit par le module of_account_tax
        for tax in taxes:
            line_account = tax.map_account(line_account)

        line_name = self.name or product.name_get()[0][1]
        return {
            'name': line_name,
            'account_id': line_account.id,
            'price_unit': self.price_unit,
            'quantity': self.qty_invoiceable,
            'discount': 0.0,
            'uom_id': product.uom_id.id,
            'product_id': product.id,
            'invoice_line_tax_ids': [(6, 0, taxes._ids)],
            'of_intervention_line_id': self.id
        }, ""

    @api.multi
    def update_vals(self):
        for line in self:
            if not line.order_line_id:
                continue
            order_line = line.order_line_id
            planned = sum(order_line.of_intervention_line_ids
                          .filtered(lambda r: (r.intervention_id.state not in ('cancel', 'postponed')
                                               and r.id != line.id))
                          .mapped('qty'))
            qty = order_line.product_uom_qty - planned
            line.update({
                'order_line_id': order_line.id,
                'product_id': order_line.product_id.id,
                'qty': qty,
                'price_unit': order_line.price_unit,
                'name': order_line.name,
                'taxe_ids': [(5, )] + [(4, tax.id) for tax in order_line.tax_id]
            })

    @api.multi
    def _prepare_intervention_line_procurement(self, group_id=False):
        self.ensure_one()
        return {
            'name': self.name,
            'origin': self.intervention_id.name,
            'date_planned': datetime.strptime(self.intervention_id.date, DEFAULT_SERVER_DATETIME_FORMAT),
            'product_id': self.product_id.id,
            'product_qty': self.qty,
            'product_uom': self.product_id.uom_id.id,
            'company_id': self.intervention_id.company_id.id,
            'group_id': group_id,
            'of_intervention_line_id': self.id,
            'location_id': self.intervention_id.address_id.property_stock_customer.id,
            'warehouse_id': self.intervention_id.warehouse_id and self.intervention_id.warehouse_id.id or False,
            'partner_dest_id': self.intervention_id.address_id.id,
        }

    @api.multi
    def _action_procurement_create(self):
        """
        Copie de sale.order.line._action_procurement_create(), adaptée pour of.planning.intervention.line
        Create procurements based on quantity ordered. If the quantity is increased, new
        procurements are created. If the quantity is decreased, no automated action is taken.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        new_procs = self.env['procurement.order']  # Empty recordset
        do_deliveries = self.env['ir.values'].get_default('of.intervention.settings', 'do_deliveries')
        verif_state = self._context.get('verif_state', True)
        rdv_skipped = self.env['of.planning.intervention']
        for line in self:
            if (verif_state and line.intervention_id.state not in ('confirm', 'done')) \
                    or not line.product_id._need_procurement() or line.order_line_id or not do_deliveries:
                continue
            if not line.intervention_id.address_id:
                rdv_skipped |= line.intervention_id
                continue
            qty = 0.0
            for proc in line.procurement_ids.filtered(lambda r: r.state != 'cancel'):
                qty += proc.product_qty
            if float_compare(qty, line.qty, precision_digits=precision) >= 0:
                continue

            if not line.intervention_id.procurement_group_id:
                vals = line.intervention_id._prepare_procurement_group()
                line.intervention_id.procurement_group_id = self.env["procurement.group"].create(vals)

            vals = line._prepare_intervention_line_procurement(group_id=line.intervention_id.procurement_group_id.id)
            vals['product_qty'] = line.qty - qty
            new_proc = self.env["procurement.order"].with_context(procurement_autorun_defer=True).create(vals)
            new_proc.message_post_with_view('mail.message_origin_link',
                                            values={'self': new_proc, 'origin': line.intervention_id},
                                            subtype_id=self.env.ref('mail.mt_note').id)
            new_procs += new_proc
        new_procs.run()
        return new_procs.with_context(errors=[rdv.name for rdv in rdv_skipped])

    @api.multi
    def _get_delivered_qty(self):
        """Computes the delivered quantity on sale order lines, based on done stock moves related to its procurements
        """
        self.ensure_one()
        qty = 0.0
        for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
            if move.location_dest_id.usage == "customer":
                # FORWARD-PORT NOTICE: "to_refund_so" to rename to "to_refund" in v11
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund_so):
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_id.uom_id)
            elif move.location_dest_id.usage != "customer" and move.to_refund_so:
                qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_id.uom_id)
        return qty


class ResPartner(models.Model):
    _inherit = "res.partner"

    intervention_partner_ids = fields.One2many(
        comodel_name='of.planning.intervention', string="Interventions client", inverse_name='partner_id')
    intervention_address_ids = fields.One2many(
        comodel_name='of.planning.intervention', string="Interventions adresse", inverse_name='address_id')
    intervention_ids = fields.Many2many(
        'of.planning.intervention', string=u"Interventions", compute="_compute_interventions")
    intervention_count = fields.Integer(string="Nb d'interventions", compute='_compute_interventions')

    @api.multi
    def _compute_interventions(self):
        interv_obj = self.sudo().env['of.planning.intervention']
        for partner in self:
            intervention_ids = interv_obj.search(
                ['|',
                    ('partner_id', 'child_of', partner.id),
                    ('address_id', 'child_of', partner.id),
                 ])
            partner.intervention_ids = intervention_ids
            partner.intervention_count = len(intervention_ids)

    @api.multi
    def _get_action_view_intervention_context(self, context={}):
        context.update({
            'default_partner_id': self.id,
            'default_address_id': self.id,
            'default_date': fields.Date.today(9),
        })
        return context

    @api.multi
    def action_view_intervention(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]

        action['domain'] = ['|', ('partner_id', 'child_of', self.ids), ('address_id', 'child_of', self.ids)]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            action['context'] = self._get_action_view_intervention_context(context)
        action = self.mapped('intervention_ids').get_action_views(self, action)
        return action


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Utilisé pour ajouter bouton Interventions à Devis (see order_id many2one field above)
    intervention_ids = fields.One2many("of.planning.intervention", "order_id", string="Interventions")

    intervention_count = fields.Integer(string="Nb d'interventions", compute='_compute_intervention_count')
    of_planned = fields.Boolean(string=u"Planifiée", compute="_compute_planned", store=True)

    @api.depends('intervention_ids')
    @api.multi
    def _compute_intervention_count(self):
        for sale_order in self:
            sale_order.intervention_count = len(sale_order.intervention_ids)

    @api.depends('order_line', 'order_line.of_intervention_state')
    def _compute_planned(self):
        for order in self:
            for line in order.order_line:
                if line.of_intervention_state not in ['confirm', 'done']:
                    order.of_planned = False
                    break
            else:
                order.of_planned = True

    @api.multi
    def action_view_intervention(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]

        if len(self._ids) == 1:
            picking_list = self.picking_ids.ids
            context = safe_eval(action['context'])
            context.update({
                'default_address_id': self.partner_shipping_id.id or False,
                'default_order_id': self.id,
                'default_picking_manual_ids': [(6, 0, picking_list)],
            })
            if self.intervention_ids:
                context['force_date_start'] = self.intervention_ids[-1].date_date
                context['search_default_order_id'] = self.id
            action['context'] = str(context)
        action = self.mapped('intervention_ids').get_action_views(self, action)
        return action

    def fiche_intervention_cacher_montant(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'fiche_intervention_cacher_montant')


class OfPlanningTag(models.Model):
    _description = u"Étiquettes d'intervention"
    _name = 'of.planning.tag'
    _order = "sequence"

    name = fields.Char(string="Nom", required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1, help="Used to order tags. Lower is better.")
    color = fields.Integer(string="Index couleur")
    active = fields.Boolean(default=True, help=u"Permet de cacher l'étiquette sans la supprimer.")
    intervention_ids = fields.Many2many(
        'of.planning.intervention', column1='tag_id', column2='intervention_id', string="Interventions")


class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        if report_name == 'of_planning.of_planning_fiche_intervention_report_template':
            self = self.sudo()
        result = super(Report, self).get_pdf(docids, report_name, html=html, data=data)
        return result


class OfMailTemplate(models.Model):
    _inherit = "of.mail.template"

    @api.model
    def _get_allowed_models(self):
        return super(OfMailTemplate, self)._get_allowed_models() + ['of.planning.intervention']


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_intervention_line_ids = fields.One2many('of.planning.intervention.line', 'order_line_id')
    of_qty_planning_done = fields.Float(
        string=u"Qté(s) réalisée(s)", compute='_compute_of_qty_planning_done', store=True,
        digits=dp.get_precision('Product Unit of Measure'), oldname='of_qty_planifiee', compute_sudo=True)
    of_intervention_state = fields.Selection(
        [('todo', u'À planifier'),
         ('confirm', u'Planifée'),
         ('done', u'Réalisée'),
         ],
        string=u"État de planification", compute="_compute_intervention_state", store=True, compute_sudo=True)

    @api.depends('of_intervention_line_ids', 'of_intervention_line_ids.qty',
                 'of_intervention_line_ids.intervention_state')
    def _compute_of_qty_planning_done(self):
        for line in self:
            lines = line.of_intervention_line_ids.filtered(lambda l: l.intervention_state in ('done', ))
            line.of_qty_planning_done = sum(lines.mapped('qty'))

    @api.depends('of_intervention_line_ids', 'of_intervention_line_ids.intervention_state')
    def _compute_intervention_state(self):
        for line in self:
            state_done = [True if state == 'done' else False
                          for state in line.of_intervention_line_ids.mapped('intervention_state')]
            state_confirm = [True if state in ('draft', 'confirm', 'done') else False
                             for state in line.of_intervention_line_ids.mapped('intervention_state')]
            if state_done and all(state_done):
                line.of_intervention_state = 'done'
            elif state_confirm and all(state_confirm):
                line.of_intervention_state = 'confirm'
            else:
                line.of_intervention_state = 'todo'

    @api.model
    def create(self, vals):
        if vals.get('order_id', False):
            order = self.env['sale.order'].browse(vals['order_id'])
            if order and order.state == 'sale':
                # Ajout d'un contexte afin de ne pas recalculer la date du BL
                # si ce dernier est lié à des RDVs d'intervention
                self = self.with_context(of_add_order_line=True)
        return super(SaleOrderLine, self).create(vals)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    of_intervention_line_id = fields.Many2one('of.planning.intervention.line', string=u"Ligne planifiée")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_intervention_ids = fields.Many2many(
        comodel_name='of.planning.intervention', string=u"RDVs d'intervention liés",
        relation='of_planning_intervention_picking_manual_rel', column1='picking_id', column2='intervention_id')
    of_intervention_count = fields.Integer(
        string=u"Nb de RDVs d'intervention liés", compute='_compute_of_intervention_count')

    @api.multi
    def _compute_of_intervention_count(self):
        for picking in self:
            picking.of_intervention_count = len(picking.of_intervention_ids)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        if self._context.get('force_read'):
            res = super(StockPicking, self.sudo()).read(fields, load)
        else:
            res = super(StockPicking, self).read(fields, load)
        return res

    @api.multi
    def action_view_interventions(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            order = self.move_lines.mapped('procurement_id').mapped('sale_line_id').mapped('order_id')
            # Un BL peut se retrouver avec uniquement des composants de kits
            if not order:
                order = self.move_lines.mapped('procurement_id').mapped('of_sale_comp_id').mapped('order_id')
            if order and len(order) > 1:
                order = order[0]
            context.update({
                'default_address_id': self.partner_id and self.partner_id.id or False,
                'default_order_id': order and order.id or False,
                'default_picking_manual_ids': [(6, 0, [self.id])],
            })
            if self.of_intervention_ids:
                context['force_date_start'] = self.of_intervention_ids[-1].date_date
            action['context'] = str(context)
            action['domain'] = "[('picking_manual_ids', 'in', %s)]" % self.id
        action = self.mapped('of_intervention_ids').get_action_views(self, action)
        return action

    @api.multi
    def button_open_picking_manual(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
        }


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def write(self, vals):
        # Lors de l'ajout d'une ligne sur un bon de commande validé, on inhibe le recalcul de la date du BL
        # si ce dernier est lié à des RDVs d'intervention
        if self._context.get('of_add_order_line', False) and vals.get('picking_id', False):
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking and picking.of_intervention_ids:
                vals['date_expected'] = picking.min_date
        return super(StockMove, self).write(vals)

    @api.multi
    def action_done(self):
        result = super(StockMove, self).action_done()

        # Update delivered quantities on intervention lines
        planning_intervention_lines = self.filtered(
            lambda move: move.procurement_id.of_intervention_line_id and move.product_id.expense_policy == 'no'
        ).mapped('procurement_id.of_intervention_line_id')
        for line in planning_intervention_lines:
            line.qty_delivered = line._get_delivered_qty()
        return result

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if isinstance(res, dict):
            interventions = self.mapped('procurement_id').mapped('of_intervention_line_id').mapped('intervention_id')
            if len(interventions) == 1:
                res['min_date'] = interventions.date
        return res


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    of_intervention_line_id = fields.Many2one('of.planning.intervention.line')
