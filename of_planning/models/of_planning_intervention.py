# -*- coding: utf-8 -*-

from __builtin__ import False
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import re
import pytz

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from odoo.tools.float_utils import float_compare


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

class OfPlanningTache(models.Model):
    _name = "of.planning.tache"
    _description = u"Planning OpenFire : Tâches"

    name = fields.Char(u'Libellé', size=64, required=True)
    description = fields.Text('Description')
    verr = fields.Boolean(u'Verrouillé')
    product_id = fields.Many2one('product.product', 'Produit')
    active = fields.Boolean('Actif', default=True)
    imp_detail = fields.Boolean(u'Imprimer Détail', help=u"""Impression du détail des tâches dans le planning semaine
Si cette option n'est pas cochée, seule la tâche la plus souvent effectuée dans la journée apparaîtra""", default=True)
    duree = fields.Float(u'Durée par défaut', digits=(12, 5), default=1.0)
    category_id = fields.Many2one('hr.employee.category', string=u"Catégorie d'employés")
    is_crm = fields.Boolean(u'Tâche CRM')
    equipe_ids = fields.Many2many('of.planning.equipe', 'equipe_tache_rel', 'tache_id', 'equipe_id', 'Équipes')

    @api.multi
    def unlink(self):
        if self.search([('id', 'in', self._ids), ('verr', '=', True)]):
            raise ValidationError(u'Vous essayez de supprimer une tâche verrouillée.')
        return super(OfPlanningTache, self).unlink()

class OfPlanningEquipe(models.Model):
    _name = "of.planning.equipe"
    _description = u"Équipe d'intervention"
    _order = "sequence, name"

    def _default_tz(self):
        return self.env.user.tz or 'Europe/Paris'

    name = fields.Char(u'Équipe', size=128, required=True)
    note = fields.Text('Description')
    employee_ids = fields.Many2many('hr.employee', 'of_planning_employee_rel', 'equipe_id', 'employee_id', u'Employés')
    active = fields.Boolean('Actif', default=True)
    category_ids = fields.Many2many('hr.employee.category', 'equipe_category_rel', 'equipe_id', 'category_id', u'Catégories')
    intervention_ids = fields.One2many('of.planning.intervention', 'equipe_id', u'Interventions liées', copy=False)
    tache_ids = fields.Many2many('of.planning.tache', 'equipe_tache_rel', 'equipe_id', 'tache_id', u'Compétences')
    hor_md = fields.Float(u'Matin début', required=True, digits=(12, 5))
    hor_mf = fields.Float('Matin fin', required=True, digits=(12, 5))
    hor_ad = fields.Float(u'Après-midi début', required=True, digits=(12, 5))
    hor_af = fields.Float(u'Après-midi fin', required=True, digits=(12, 5))
    sequence = fields.Integer(u'Séquence', help=u"Ordre d'affichage (plus petit en premier)")
    color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D")
    color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0")
    tz = fields.Selection(
        _tz_get, string='Fuseau horaire', required=True, default=lambda self: self._default_tz(),
        help="Le fuseau horaire de l'équipe d'intervention")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)

    @api.depends('tz')
    def _compute_tz_offset(self):
        for equipe in self:
            equipe.tz_offset = datetime.now(pytz.timezone(equipe.tz or 'GMT')).strftime('%z')

    @api.onchange('employee_ids')
    def onchange_employees(self):
        if not self.category_ids:
            category_ids = []
            for employee in self.employee_ids:
                for category in employee.category_ids:
                    if category.id not in category_ids:
                        category_ids.append(category.id)
            if category_ids:
                self.category_ids = category_ids

    @api.onchange('hor_md', 'hor_mf', 'hor_ad', 'hor_af')
    def onchange_horaires(self):
        hors = (self.hor_md, self.hor_mf, self.hor_ad, self.hor_af)
        if all(hors):
            for hor in hors:
                if hor > 24:
                    raise ValidationError(u"L'heure doit être inférieure ou égale à 24")
            if hors[0] > hors[1] or hors[2] > hors[3]:
                raise ValidationError(u"L'heure de début ne peut pas être supérieure à l'heure de fin")
            if(hors[1] > hors[2]):
                raise ValidationError(u"L'heure de l'après-midi ne peut pas être inférieure à l'heure du matin")

    @api.model
    def get_working_hours_fields(self):
        return {
            "morning_start_field": "hor_md",
            "morning_end_field": "hor_mf",
            "afternoon_start_field": "hor_ad",
            "afternoon_end_field": "hor_af",
        }

class OfPlanningInterventionRaison(models.Model):
    _name = "of.planning.intervention.raison"
    _description = u"Raisons d'intervention reportée"

    name = fields.Char(u'Libellé', size=128, required=True)

class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _description = "Planning d'intervention OpenFire"
    _inherit = ["of.readgroup", "of.calendar.mixin", 'mail.thread']
    _order = 'date'

    name = fields.Char(string=u'Libellé', required=True)
    date = fields.Datetime(string='Date intervention', required=True)
    date_deadline = fields.Datetime(compute="_compute_date_deadline", string='Date Fin', store=True)
    duree = fields.Float(string=u'Durée intervention', required=True, digits=(12, 5))
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.uid)
    partner_id = fields.Many2one('res.partner', string='Client', compute='_compute_partner_id', store=True)
    address_id = fields.Many2one('res.partner', string='Adresse')
    partner_city = fields.Char(related='address_id.city', string="Ville")
    raison_id = fields.Many2one('of.planning.intervention.raison', string='Raison')
    tache_id = fields.Many2one('of.planning.tache', string='Tâche', required=True)
    equipe_id = fields.Many2one('of.planning.equipe', string=u'Équipe', required=True, oldname='poseur_id')
    employee_ids = fields.Many2many(related='equipe_id.employee_ids', string='Intervenants', readonly=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', u'Confirmé'),
        ('done', u'Réalisé'),
        ('unfinished', u'Inachevé'),
        ('cancel', u'Annulé'),
        ('postponed', u'Reporté'),
        ], string=u'État', index=True, readonly=True, default='draft')
    company_id = fields.Many2one('res.company', string='Magasin', default=lambda self: self.env.user.company_id.id)
    tag_ids = fields.Many2many('of.planning.tag', column1='intervention_id', column2='tag_id', string=u'Étiquettes')
    description = fields.Html(string='Description')  # Non utilisé, changé pour notes intervention
    hor_md = fields.Float(string=u'Matin début', required=True, digits=(12, 5))
    hor_mf = fields.Float(string='Matin fin', required=True, digits=(12, 5))
    hor_ad = fields.Float(string=u'Après-midi début', required=True, digits=(12, 5))
    hor_af = fields.Float(string=u'Après-midi fin', required=True, digits=(12, 5))
    hor_sam = fields.Boolean(string='Samedi')
    hor_dim = fields.Boolean(string='Dimanche')
    tz = fields.Selection(related="equipe_id.tz", readonly=True)
    tz_offset = fields.Char(related="equipe_id.tz_offset", readonly=True)

    # 3 champs ajoutés pour la vue map
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')
    precision = fields.Selection(related='address_id.precision')
    partner_name = fields.Char(related='partner_id.name')

    category_id = fields.Many2one(related='tache_id.category_id', string=u"Type de tâche")
    verif_dispo = fields.Boolean(string=u'Vérif', help=u"Vérifier la disponibilité de l'équipe sur ce créneau", default=True)
    gb_employee_id = fields.Many2one('hr.employee', compute=lambda *a, **k: {}, search='_search_gb_employee_id',
                                     string="Intervenant", of_custom_groupby=True)

    color_ft = fields.Char(related="equipe_id.color_ft", readonly=True)
    color_bg = fields.Char(related="equipe_id.color_bg", readonly=True)

    order_id = fields.Many2one("sale.order", string="Commande associée")
    of_notes_intervention = fields.Html(related='order_id.of_notes_intervention', readonly=True)
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)
    cleantext_description = fields.Text(compute='_compute_cleantext_description')
    cleantext_intervention = fields.Text(compute='_compute_cleantext_intervention', store=True)
    jour = fields.Char("Jour", compute="_compute_jour")
    date_date = fields.Date(string='Jour intervention', compute='_compute_date_date', search='_search_date_date', readonly=True)

    template_id = fields.Many2one('of.planning.intervention.template', string=u"Modèle d'intervention")
    number = fields.Char(String=u"Numéro", copy=False)
    calendar_name = fields.Char(string="Calendar Name", compute="_compute_calendar_name")

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

    @api.depends('date', 'duree', 'hor_md', 'hor_mf', 'hor_ad', 'hor_af', 'hor_sam', 'hor_dim')
    def _compute_date_deadline(self):
        compare_precision = 5
        for intervention in self:
            if intervention.hor_md > 24 or intervention.hor_mf > 24 or intervention.hor_ad > 24 or intervention.hor_af > 24:
                raise UserError(u"L'heure doit être inferieure ou égale à 24")
            if intervention.hor_mf < intervention.hor_md or intervention.hor_ad < intervention.hor_mf:
                raise UserError(u"L'heure de début ne peut pas être supérieure à l'heure de fin")
            if intervention.hor_ad < intervention.hor_mf:
                raise UserError(u"L'heure de l'après-midi ne peut pas être inférieure à l'heure du matin")

            if not intervention.date:
                return
            if not intervention.duree:
                return

            # Datetime UTC
            dt_utc = datetime.strptime(intervention.date, "%Y-%m-%d %H:%M:%S")
            # Datetime local
            dt_local = fields.Datetime.context_timestamp(intervention, dt_utc)

            weekday = dt_local.weekday()
            if weekday == 5 and not intervention.hor_sam:
                raise UserError(u"L'équipe ne travaille pas le samedi")
            elif weekday == 6 and not intervention.hor_dim:
                raise UserError(u"L'équipe ne travaille pas le dimanche")

            duree_repos = intervention.hor_ad - intervention.hor_mf
            duree_matin = intervention.hor_mf - intervention.hor_md
            duree_apres = intervention.hor_af - intervention.hor_ad
            duree_jour = duree_matin + duree_apres

            dt_heure = dt_local.hour + (dt_local.minute + dt_local.second / 60.0) / 60.0
            # Déplacement de l'horaire de début au début de la journée pour faciliter le calcul
            duree = intervention.duree
            if float_compare(dt_heure, intervention.hor_md, compare_precision) >= 0 and float_compare(intervention.hor_mf, dt_heure, compare_precision) >= 0:
                # intervention.hor_md <= dt_heure <= intervention.hor_mf
                duree += dt_heure - intervention.hor_md
            elif float_compare(dt_heure, intervention.hor_ad, compare_precision) >= 0 and float_compare(intervention.hor_af, dt_heure, compare_precision) >= 0:
                # intervention.hor_ad <= dt_heure <= intervention.hor_af:
                duree += duree_matin + dt_heure - intervention.hor_ad
            else:
                # L'horaire de debut des travaux est en dehors des heures de travail
                raise UserError(u"Il faut respecter l'horaire de travail")
            dt_local -= timedelta(hours=dt_heure)

            # Calcul du nombre de jours
            jours, duree = duree // duree_jour, duree % duree_jour
            # Correction erreur d'arrondi
            if duree * 60 < 1:  # ça dépasse de moins d'une minute
                # Le travail se termine à la fin de la journée
                duree = duree_jour
                jours -= 1

            if not (intervention.hor_sam and intervention.hor_dim):
                # Deplacement de l'horaire de debut au debut de la semaine pour faciliter le calcul
                # Le debut de la semaine peut eventuellement etre un dimanche matin
                jours_sem = (weekday + intervention.hor_dim) % 6
                dt_local -= timedelta(days=jours_sem)
                jours += jours_sem

                # Ajout des jours de repos a la duree de la tache pour arriver la meme date de fin
                jours += (2 - intervention.hor_sam - intervention.hor_dim) * (jours // (5 + intervention.hor_sam + intervention.hor_dim))

            # Ajout des heures non travaillées de la derniere journée
            duree += intervention.hor_md + (duree > duree_matin and duree_repos)

            # Calcul de la nouvelle date
            dt_local += timedelta(days=jours, hours=duree)
            # Conversion en UTC
            dt_utc = dt_local - dt_local.tzinfo._utcoffset
            date_deadline = dt_utc.strftime("%Y-%m-%d %H:%M:%S")
            intervention.date_deadline = date_deadline

    @api.depends('address_id', 'address_id.parent_id')
    def _compute_partner_id(self):
        for intervention in self:
            partner = intervention.address_id or False
            if partner:
                while partner.parent_id:
                    partner = partner.parent_id
            intervention.partner_id = partner and partner.id

    def _search_gb_employee_id(self, operator, value):
        return [('equipe_id.employee_ids', operator, value)]

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

    @api.depends('date')
    def _compute_jour(self):
        for inter in self:
            t = ''
            if inter.date:
                dt = datetime.strptime(inter.date, DEFAULT_SERVER_DATETIME_FORMAT)
                dt = fields.Datetime.context_timestamp(self, dt)  # openerp's ORM method
                t = dt.strftime("%A").capitalize()  # the day_name is Sunday here
            inter.jour = t

    @api.depends('date')
    def _compute_date_date(self):
        for inter in self:
            inter.date_date = inter.date

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

    @api.onchange('equipe_id')
    def _onchange_equipe_id(self):
        equipe = self.equipe_id
        if equipe.hor_md and equipe.hor_mf and equipe.hor_ad and equipe.hor_af:
            self.hor_md = equipe.hor_md
            self.hor_mf = equipe.hor_mf
            self.hor_ad = equipe.hor_ad
            self.hor_af = equipe.hor_af

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
        for intervention in self:
            if intervention.verif_dispo:
                rdv = self.search([
                    ('equipe_id', '=', intervention.equipe_id.id),
                    ('date', '<', intervention.date_deadline),
                    ('date_deadline', '>', intervention.date),
                    ('id', '!=', intervention.id),
                    ('state', 'not in', ('cancel', 'postponed')),
                ])
                if rdv:
                    raise ValidationError(u'Cette équipe a déjà %s rendez-vous sur ce créneau' % (len(rdv),))

    @api.multi
    def _affect_number(self):
        for interv in self:
            if interv.template_id and interv.state in ('confirm', 'done', 'unfinished', 'postponed') and not interv.number:
                interv.write({'number': self.template_id.sequence_id.next_by_id()})

    @api.model
    def create(self, vals):
        res = super(OfPlanningIntervention, self).create(vals)
        res.do_verif_dispo()
        res._affect_number()
        return res

    @api.multi
    def write(self, vals):
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
                    msg_erreur % (self.name, u'Il faut configurer les comptes de revenus pour la catégorie du produit\n'))

        # Mapping des comptes par taxe induit par le module of_account_tax
        for tax in taxes:
            line_account = tax.map_account(line_account)

        pricelist = partner.property_product_pricelist
        company = self._get_invoicing_company(partner)
        from_currency = company.currency_id

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
    _description = "Étiquettes d'intervention"
    _name = 'of.planning.tag'

    name = fields.Char(string='Nom', required=True, translate=True)
    color = fields.Integer(string='Index couleur')
    active = fields.Boolean(default=True, help="Le champ 'Active' vous permet de cacher l'étiquette sans la supprimer.")
    intervention_ids = fields.Many2many('of.planning.intervention', column1='tag_id', column2='intervention_id', string='Interventions')

class OfMailTemplate(models.Model):
    _inherit = "of.mail.template"

    @api.model
    def _get_allowed_models(self):
        return super(OfMailTemplate, self)._get_allowed_models() + ['of.planning.intervention']
