# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import re
import requests
import urllib

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval

import odoo.addons.decimal_precision as dp
from odoo.addons.of_utils.models.of_utils import se_chevauchent, float_2_heures_minutes, heures_minutes_2_float, \
    compare_date


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
    # api.depends dans of.planning.intervention
    of_changed_intervention_id = fields.Many2one('of.planning.intervention', string=u"Dernier RDV modifié")
    of_est_intervenant = fields.Boolean(string=u"Est intervenant ?", default=False)

    @api.multi
    def peut_faire(self, tache_id, all_required=False):
        """
        Renvoie True si les employés dans self peuvent réaliser la tâche. Sauf si all_required=True, il suffit qu'un
        des employés puisse réaliser la tâche pour que la fonction renvoie True
        :param tache_id: La tâche en question
        :param all_required: True si tous les employés doivent savoir réaliser la tâche
        :return: True si peut faire, False sinon
        :rtype Boolean
        """
        if all_required:
            return len(self.filtered(lambda e: (tache_id not in e.of_tache_ids) and not e.of_toutes_taches)) == 0
        return len(self.filtered(lambda e: (tache_id in e.of_tache_ids) or e.of_toutes_taches))

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
        tache_id = self._context.get('tache_prio_id')
        tache = tache_id and self.env['of.planning.tache'].browse(tache_id) or False
        result = []
        for employee in self:
            peut_faire = employee.peut_faire(tache) if tache else True
            result.append((employee.id, "%s%s%s" % ('' if peut_faire else '(',
                                                    employee.name,
                                                    '' if peut_faire else ')')))
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
Cette granularité permet, à la saisie d'une intervention à programmer,
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
        return data


class OfPlanningTache(models.Model):
    _name = "of.planning.tache"
    _description = u"Planning OpenFire : Tâches"

    name = fields.Char(u"Libellé", size=64, required=True)
    description = fields.Text("Description")
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

    @api.multi
    def _compute_employee_ids(self):
        intervenants = self.env['hr.employee'].search([('of_est_intervenant', '=', True)])
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

    @api.multi
    def _prepare_invoice_line(self, intervention):
        self.ensure_one()
        product = self.product_id
        partner = intervention.partner_id
        if not intervention.fiscal_position_id and not partner.property_account_position_id:
            return {}, u"Veuillez définir une position fiscale pour l'intervention %s" % self.name
        fiscal_position = intervention.fiscal_position_id or partner.property_account_position_id
        taxes = product.taxes_id
        if partner.company_id:
            taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
        taxes = fiscal_position and fiscal_position.map_tax(taxes, product, partner) or []

        line_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not line_account:
            return {}, u'Il faut configurer les comptes de revenus pour la catégorie du produit %s.\n' % product.name

        # Mapping des comptes par taxe induit par le module of_account_tax
        for tax in taxes:
            line_account = tax.map_account(line_account)

        pricelist = partner.property_product_pricelist
        company = intervention._get_invoicing_company(partner)

        if pricelist.discount_policy == 'without_discount':
            from_currency = company.currency_id
            price_unit = from_currency.compute(product.lst_price, pricelist.currency_id)
        else:
            price_unit = product.with_context(pricelist=pricelist.id).price
        price_unit = self.env['account.tax']._fix_tax_included_price(price_unit, product.taxes_id, taxes)
        return {
                   'name'                : product.name_get()[0][1],
                   'account_id'          : line_account.id,
                   'price_unit'          : price_unit,
                   'quantity'            : 1.0,
                   'discount'            : 0.0,
                   'uom_id'              : product.uom_id.id,
                   'product_id'          : product.id,
                   'invoice_line_tax_ids': [(6, 0, taxes._ids)],
                   }, ""


class OfPlanningEquipe(models.Model):
    _name = "of.planning.equipe"
    _description = u"Équipe d'intervention"
    _order = "sequence, name"

    @api.model
    def _domain_employee_ids(self):
        return [('of_est_intervenant', '=', True)]

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
        return [('of_est_intervenant', '=', True)]

    # Default #

    @api.model
    def _default_company(self):
        # Pour les objets du planning, le choix de société se fait par un paramètre de config
        if self.env['ir.values'].get_default('of.intervention.settings', 'company_choice') == 'user':
            return self.env['res.company']._company_default_get('of.planning.intervention')
        return False

    # Champs #

    # Header
    state = fields.Selection(
        [
            ('draft', "Brouillon"),
            ('confirm', u"Confirmé"),
            ('done', u"Réalisé"),
            ('unfinished', u"Inachevé"),
            ('cancel', u"Annulé"),
            ('postponed', u"Reporté"),
        ], string=u"État", index=True, readonly=True, default='draft', track_visibility='onchange')
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
    partner_id = fields.Many2one('res.partner', string="Client", compute='_compute_partner_id', store=True)
    address_id = fields.Many2one('res.partner', string="Adresse", track_visibility='onchange')
    address_city = fields.Char(related='address_id.city', string="Ville", oldname="partner_city")
    address_zip = fields.Char(related='address_id.zip')
    secteur_id = fields.Many2one(related='address_id.of_secteur_tech_id', readonly=True)
    user_id = fields.Many2one('res.users', string="Utilisateur", default=lambda self: self.env.uid)
    company_id = fields.Many2one('res.company', string='Magasin', required=True, default=lambda s: s._default_company())
    name = fields.Char(string=u"Libellé", required=True)
    tag_ids = fields.Many2many('of.planning.tag', column1='intervention_id', column2='tag_id', string=u"Étiquettes")

    # Rubrique Planification
    template_id = fields.Many2one('of.planning.intervention.template', string=u"Modèle d'intervention")
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche", required=True)
    tache_categ_id = fields.Many2one(related="tache_id.tache_categ_id", readonly=True)
    forcer_dates = fields.Boolean(
        "Forcer les dates", default=False, help=u"/!\\ outrepasser les horaires des intervenants")
    jour = fields.Char("Jour", compute="_compute_jour")
    date = fields.Datetime(string="Date intervention", required=True, track_visibility='always')
    date_date = fields.Date(
        string="Jour intervention", compute='_compute_date_date', search='_search_date_date', readonly=True)
    duree = fields.Float(string=u"Durée intervention", required=True, digits=(12, 5), track_visibility='always')
    duree_debut_fin = fields.Float(
        string=u"Durée entre le début et la fin", compute="_compute_duree_debut_fin", store=True,
        help=u"Prend en compte le temp de pause au milieu du RDV")
    jour_fin = fields.Char("Jour fin", compute="_compute_jour")
    date_deadline = fields.Datetime(
        compute="_compute_date_deadline", string="Date fin", store=True, track_visibility='always')
    jour_fin_force = fields.Char(u"Jour fin forcé", compute="_compute_jour")
    date_deadline_forcee = fields.Datetime(string=u"Date fin (forcée)")
    horaire_du_jour = fields.Text(string=u"Horaires du jour", compute="_compute_horaire_du_jour")
    verif_dispo = fields.Boolean(
        string=u"Vérif chevauchement", default=True,
        help=u"Vérifier que cette intervention n'en chevauche pas une autre")

    # Rubrique Documents liés
    order_id = fields.Many2one(
        "sale.order", string=u"Commande associée",
        domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")

    # Onglet Description
    description = fields.Html(string="Description")

    # Onglet Notes
    of_notes_intervention = fields.Html(related='order_id.of_notes_intervention', readonly=True)
    of_notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)

    # Messages d'alerte
    alert_hors_creneau = fields.Boolean(string=u"RDV hors des créneaux", compute="_compute_date_deadline")
    alert_coherence_date = fields.Boolean(string=u"Incohérence dans les dates", compute="_compute_alert_coherence_date")
    alert_incapable = fields.Boolean(string="Aucun intervenant apte", compute="_compute_alert_incapable")

    # Pour recherche
    gb_employee_id = fields.Many2one(
        'hr.employee', compute=lambda *a, **k: {}, search='_search_gb_employee_id', string="Intervenant",
        of_custom_groupby=True)

    # Vue Calendar / Planning / Map
    calendar_name = fields.Char(string="Calendar Name", compute="_compute_calendar_name")  # vue Calendar
    tache_name = fields.Char(related='tache_id.name', readonly=True)  # vue Planning
    partner_name = fields.Char(related='partner_id.name')  # vue Planning, vue Map
    tz = fields.Selection(_tz_get, compute='_compute_tz', string="Fuseau horaire")  # vue Calendar
    tz_offset = fields.Char(compute='_compute_tz_offset', string="Timezone offset", invisible=True)  # vue Calendar
    geo_lat = fields.Float(related='address_id.geo_lat', readonly=True)  # vue Map
    geo_lng = fields.Float(related='address_id.geo_lng', readonly=True)  # vue Map
    precision = fields.Selection(related='address_id.precision', readonly=True)  # vue Map
    of_color_ft = fields.Char(related="employee_main_id.of_color_ft", readonly=True, oldname='color_ft')  # vue Calendar
    of_color_bg = fields.Char(related="employee_main_id.of_color_bg", readonly=True, oldname='color_bg')  # vue Calendar

    # Divers / à classer / inclassable
    category_id = fields.Many2one(related='tache_id.category_id', string=u"Catégorie d'employé")
    # pour faire des stats sur comment sont créés les RDVs
    origin_interface = fields.Char(string=u"Origine création", default=u"Manuelle")
    # cleantext: afficher les champs Html dans des vues liste sans les balises html exple: <p> description </p>
    cleantext_description = fields.Text(compute='_compute_cleantext_description')
    cleantext_intervention = fields.Text(compute='_compute_cleantext_intervention', store=True)
    interv_before_id = fields.Many2one(
        'of.planning.intervention', compute="_compute_interventions_before_after", store=True)
    interv_after_id = fields.Many2one(
        'of.planning.intervention', compute="_compute_interventions_before_after", store=True)
    before_to_this = fields.Float(compute="_compute_interval", store=True, digits=(12, 5))

    line_ids = fields.One2many('of.planning.intervention.line', 'intervention_id', string='Lignes de facturation')
    lien_commande = fields.Boolean(string='Facturation sur commande', compute='_compute_lien_commande')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale")
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related="company_id.currency_id")

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total HT', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Sous-total TTC', readonly=True, store=True)
    product_ids = fields.Many2many('product.product', related='template_id.product_ids')
    invoice_ids = fields.One2many('account.invoice', string="Factures", compute="_compute_invoice_ids")
    invoice_count = fields.Integer(string="Nombre de factures", compute="_compute_invoice_ids")

    picking_id = fields.Many2one(
        comodel_name='stock.picking', string=u"BL associé",
        domain="[('id', 'in', picking_domain and picking_domain[0] and picking_domain[0][2] or False)]")
    picking_domain = fields.Many2many(comodel_name='stock.picking', compute='_compute_picking_domain')

    # Compute

    @api.multi
    @api.depends('employee_ids')
    def _compute_employee_main_id(self):
        for interv in self:
            if interv.employee_ids:
                interv.employee_main_id = interv.employee_ids[0]

    @api.depends('address_id', 'address_id.parent_id')
    def _compute_partner_id(self):
        for interv in self:
            partner = interv.address_id or False
            if partner:
                while partner.parent_id:
                    partner = partner.parent_id
            interv.partner_id = partner and partner.id

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

    @api.depends('date', 'date_deadline')
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
                # Pour des raisons pratiques on limite la recherche des horaires à une semaine après la date d'intervention
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
                # Conversion en UTC
                date_deadline_utc_dt = date_deadline_locale_dt - date_deadline_locale_dt.tzinfo._utcoffset
                date_deadline_str = date_deadline_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                interv.date_deadline = date_deadline_str
                interv.alert_hors_creneau = False

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
            tz = interv.employee_ids and interv.employee_ids[0].tz or 'GMT'
            interv.tz_offset = datetime.now(pytz.timezone(tz)).strftime('%z')

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

    @api.depends('employee_main_id')
    def _compute_interventions_before_after(self):
        return  # Temporary 'fix'
        # Cette fonction n'a jamais eu le fonctionnement voulu à cause d'une erreur sur le comparateur
        # Nous devons modifier soit le compute pour avoir un calcul plus précis ne prenant que les rdv impactés
        # Soit modifier l'appel du calcul pour ne plus être un compute.
        interv_obj = self.env['of.planning.intervention']
        for interv in self:
            if compare_date(interv.date, fields.Datetime.now(), compare="<") or \
                    not compare_date(interv.date, interv.employee_main_id.of_changed_intervention_id.date):
                continue
            if interv.interv_before_id and interv.interv_before_id == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date)
                                                       + relativedelta(hour=0, minute=0, second=0))
                interv.interv_before_id = interv_obj.search(
                    [
                        ('date_deadline', '<=', interv.date),
                        ('date', '>=', limit_date),
                        ('employee_main_id', '=', interv.employee_main_id.id)
                    ], order='date DESC', limit=1)
            if interv.interv_after_id and interv.interv_after_id == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date)
                                                       + relativedelta(days=1, hour=0, minute=0, second=0))
                interv.interv_after_id = interv_obj.search(
                    [
                        ('date', '>=', interv.date_deadline),
                        ('date', '<=', limit_date),
                        ('employee_main_id', '=', interv.employee_main_id.id)
                    ], order='date ASC', limit=1)
            if not interv.interv_before_id or interv == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date)
                                                       + relativedelta(hour=0, minute=0, second=0))
                res = interv_obj.search(
                    [
                        ('date_deadline', '<=', interv.date),
                        ('date', '>=', limit_date),
                        ('employee_main_id', '=', interv.employee_main_id.id)
                    ], order='date DESC', limit=1)
                if res:
                    interv.interv_before_id = res
            if not interv.interv_after_id or interv == interv.employee_main_id.of_changed_intervention_id:
                limit_date = fields.Datetime.to_string(fields.Datetime.from_string(interv.date)
                                                       + relativedelta(days=1, hour=0, minute=0, second=0))
                res = interv_obj.search(
                    [
                        ('date', '>=', interv.date_deadline),
                        ('date', '<=', limit_date),
                        ('employee_main_id', '=', interv.employee_main_id.id)
                    ], order='date ASC', limit=1)
                if res:
                    interv.interv_after_id = res

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
            except Exception as e:
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
        for intervention in self:
            intervention.price_subtotal = sum(intervention.line_ids.mapped('price_subtotal'))
            intervention.price_tax = sum(intervention.line_ids.mapped('price_tax'))
            intervention.price_total = sum(intervention.line_ids.mapped('price_total'))

    @api.depends('line_ids', 'line_ids.invoice_line_ids', 'order_id', 'order_id.invoice_ids')
    def _compute_invoice_ids(self):
        for rdv in self:
            invoices = rdv.line_ids.mapped('invoice_line_ids').mapped('invoice_id')
            if rdv.order_id:
                for invoice in rdv.order_id.invoice_ids:
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
                picking_list = intervention.order_id.picking_ids.ids
            intervention.picking_domain = picking_list

    # Search #

    def _search_employee_main_id(self, operator, operand):
        intervs = self.search([])
        res = safe_eval("intervs.filtered(lambda r: r.employee_main_id %s %s)" % (operator, operand), {'intervs': intervs})
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

    def _search_gb_employee_id(self, operator, value):
        return [('employee_ids', operator, value)]

    # Constraints #

    @api.constrains('date_deadline_forcee', 'forcer_dates', 'date', 'duree')
    def check_coherence_date_forcee(self):
        for interv in self:
            if interv.alert_coherence_date:
                raise UserError(
                    _(u"Attention /!\ la date de fin doit être au moins égale à la date de début + la durée"))

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

    @api.onchange('address_id')
    def _onchange_address_id(self):
        name = False
        if self.address_id:
            name = [self.address_id.name_get()[0][1]]
            for field in ('zip', 'city'):
                val = getattr(self.address_id, field)
                if val:
                    name.append(val)
            self.fiscal_position_id = self.address_id.commercial_partner_id.property_account_position_id
            # Pour les objets du planning, le choix de la société se fait par un paramètre de config
            company_choice = self.env['ir.values'].get_default(
                'of.intervention.settings', 'company_choice') or 'contact'
            if company_choice == 'contact' and self.address_id.company_id:
                self.company_id = self.address_id.company_id.id
        self.name = name and " ".join(name) or "Intervention"

    @api.onchange('template_id')
    def onchange_template_id(self):
        intervention_line_obj = self.env['of.planning.intervention.line']
        template = self.template_id
        if self.state == "draft" and template:
            self.tache_id = template.tache_id
            if not self.lien_commande and not self.fiscal_position_id:
                self.fiscal_position_id = template.fiscal_position_id
            if self.line_ids:
                new_lines = self.line_ids
            else:
                new_lines = intervention_line_obj
            for line in template.line_ids:
                data = line.get_intervention_line_values()
                data['intervention_id'] = self.id
                new_lines += intervention_line_obj.new(data)
            new_lines.compute_taxes()
            self.line_ids = new_lines

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        if self.tache_id:
            if self.tache_id.duree:
                self.duree = self.tache_id.duree
            if self.tache_id.fiscal_position_id and not self.fiscal_position_id:
                self.fiscal_position_id = self.tache_id.fiscal_position_id
            if self.tache_id.product_id:
                self.line_ids.new({
                    'intervention_id': self.id,
                    'product_id'     : self.tache_id.product_id.id,
                    'qty'            : 1,
                    'price_unit'     : self.tache_id.product_id.lst_price,
                    'name'           : self.tache_id.product_id.name,
                    })
                self.line_ids.compute_taxes()

    @api.onchange('forcer_dates')
    def _onchange_forcer_dates(self):
        if self.forcer_dates and self.duree and self.date:
            heures, minutes = float_2_heures_minutes(self.duree)
            self.date_deadline_forcee = fields.Datetime.to_string(
                fields.Datetime.from_string(self.date) + relativedelta(hours=heures, minutes=minutes))

    @api.onchange('order_id')
    def onchange_order_id(self):
        picking_list = []
        if self.order_id:
            picking_list = self.order_id.picking_ids.ids
        self.picking_domain = picking_list
        if self.picking_id and self.picking_id.id not in picking_list:
            self.picking_id = False
        res = {'domain': {'picking_id': [('id', 'in', picking_list)]}}
        return res

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
        if 'date' in vals:
            # Tronqué à la minute
            vals['date'] = vals['date'][:17] + '00'
        res = super(OfPlanningIntervention, self).create(vals)
        res.do_verif_dispo()
        res._affect_number()

        # Si BL associé, on met à jour la date du BL en fonction de la date d'intervention
        if 'picking_id' in vals and 'date' in vals:
            if res.picking_id:
                res.picking_id.min_date = res.date

        return res

    @api.multi
    def write(self, vals):
        if 'date' in vals:
            # Tronqué à la minute
            vals['date'] = vals['date'][:17] + '00'
        super(OfPlanningIntervention, self).write(vals)
        self._affect_number()

        # Si BL associé, on met à jour la date du BL en fonction de la date d'intervention
        if 'picking_id' in vals or 'date' in vals:
            for rdv in self:
                if rdv.picking_id:
                    rdv.picking_id.min_date = rdv.date

        return True

    @api.multi
    def _write(self, vals):
        res = super(OfPlanningIntervention, self)._write(vals)
        if vals.get('employee_ids') or vals.get('date') or vals.get('date_deadline') or vals.get('verif_dispo'):
            self.do_verif_dispo()
        return res

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
            if interv.lien_commande:
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
            'default_composition_mode': 'comment'
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
    def button_import_order_line(self):
        self.ensure_one()
        line_obj = self.env['of.planning.intervention.line']
        if not self.order_id:
            raise UserError(u"Il n'y a pas de commande liée a l'intervention.")
        self.fiscal_position_id = self.order_id.fiscal_position_id
        in_use = self.line_ids.mapped('order_line_id')._ids
        for line in self.order_id.order_line.filtered(lambda l: l.id not in in_use):
            qty = line.product_uom_qty - sum(line.of_intervention_line_ids \
                                             .filtered(lambda r: r.intervention_id.state not in ('cancel', 'postponed')) \
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

    @api.multi
    def button_update_lines(self):
        self.ensure_one()
        self.line_ids.update_vals()

    # Autres

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

    @api.multi
    def do_verif_dispo(self):
        # Vérification de la validité du créneau: chevauchement
        interv_obj = self.env['of.planning.intervention']
        for interv in self:
            if interv.verif_dispo:
                rdv = interv_obj.search([
                    # /!\ conserver .ids : ._ids est un tuple et génère une erreur à l'évaluation
                    ('employee_ids', 'in', interv.employee_ids.ids),
                    ('date', '<', interv.date_deadline),
                    ('date_deadline', '>', interv.date),
                    ('id', '!=', interv.id),
                    ('state', 'not in', ('cancel', 'postponed')),
                ], limit=1)
                if rdv:
                    raise ValidationError(u"L'employé %s a déjà au moins un rendez-vous sur ce créneau." %
                                          (rdv.employee_ids & interv.employee_ids)[0].name)

    @api.multi
    def _affect_number(self):
        for interv in self:
            if interv.template_id and interv.state in ('confirm', 'done', 'unfinished', 'postponed') and not interv.number:
                interv.write({'number': self.template_id.sequence_id.next_by_id()})

    @api.multi
    def _get_invoicing_company(self, partner):
        return self.company_id or partner.company_id

    @api.multi
    def _prepare_invoice_lines(self):
        self.ensure_one()
        lines_data = []
        error = ''
        for line in self.line_ids:
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
            return (False,
                    msg_erreur % (self.name, u'Pas de partenaire défini'))
        pricelist = partner.property_product_pricelist
        lines_data, error = self._prepare_invoice_lines()
        if error:
            return (False,
                    msg_erreur % (self.name, error))
        if not lines_data:
            line_data, error = self.tache_id._prepare_invoice_line(self)
            if error:
                return (False,
                        msg_erreur % (self.name, error))
            if line_data:
                lines_data = [(0, 0, line_data)]
        if not lines_data:
            return (False,
                    msg_erreur % (self.name, u"Aucune ligne facturable."))
        company = self._get_invoicing_company(partner)
        fiscal_position_id = self.fiscal_position_id.id or partner.property_account_position_id.id

        journal_id = (self.env['account.invoice'].with_context(company_id=company.id)
                      .default_get(['journal_id'])['journal_id'])
        if not journal_id:
            return (False,
                    msg_erreur % (self.name, u"Vous devez définir un journal des ventes pour cette société (%s)." % company.name))
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
                                                           'planningview_color_filter',
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


class OfPlanningInterventionLine(models.Model):
    _name = "of.planning.intervention.line"

    intervention_id = fields.Many2one(
        'of.planning.intervention', string='Intervention', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='intervention_id.partner_id')
    company_id = fields.Many2one('res.company', related='intervention_id.company_id', string=u'Société')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, related="company_id.currency_id")

    order_line_id = fields.Many2one('sale.order.line', string='Ligne de commande')
    product_id = fields.Many2one('product.product', string='Article')
    price_unit = fields.Monetary(
        string='Prix unitaire', digits=dp.get_precision('Product Price'), default=0.0, currency_field='currency_id'
    )
    qty = fields.Float(string=u'Qté', digits=dp.get_precision('Product Unit of Measure'))
    name = fields.Text(string='Description')
    taxe_ids = fields.Many2many('account.tax', string="TVA")
    discount = fields.Float(string='Remise (%)', digits=dp.get_precision('Discount'), default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total HT', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Sous-total TTC', readonly=True, store=True)

    intervention_state = fields.Selection(related="intervention_id.state", store=True)
    invoice_line_ids = fields.One2many('account.invoice.line', 'of_intervention_line_id', string=u"Ligne de facturation")

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
                'price_tax'     : taxes['total_included'] - taxes['total_excluded'],
                'price_total'   : taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                })

    @api.onchange('product_id')
    def _onchange_product(self):
        product = self.product_id
        self.qty = 1
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
    def compute_taxes(self):
        for line in self:
            product = line.product_id
            partner = line.partner_id
            fiscal_position = line.intervention_id.fiscal_position_id
            taxes = product.taxes_id
            if partner.company_id:
                taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes, product, partner)
            line.taxe_ids = taxes

    @api.multi
    def _prepare_invoice_line(self):
        self.ensure_one()
        product = self.product_id
        partner = self.partner_id
        if not self.intervention_id.fiscal_position_id:
            return {}, u"Veuillez définir une position fiscale pour l'intervention %s" % self.name
        fiscal_position = self.intervention_id.fiscal_position_id
        taxes = self.taxe_ids
        if partner.company_id and taxes:
            taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
        elif not taxes and fiscal_position:
            taxes = fiscal_position.map_tax(taxes, product, partner)

        line_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not line_account:
            return {}, u'Il faut configurer les comptes de revenus pour la catégorie du produit %s.\n' % product.name

        # Mapping des comptes par taxe induit par le module of_account_tax
        for tax in taxes:
            line_account = tax.map_account(line_account)

        return {
            'name'                   : product.name_get()[0][1],
            'account_id'             : line_account.id,
            'price_unit'             : self.price_unit,
            'quantity'               : self.qty,
            'discount'               : 0.0,
            'uom_id'                 : product.uom_id.id,
            'product_id'             : product.id,
            'invoice_line_tax_ids'   : [(6, 0, taxes._ids)],
            'of_intervention_line_id': self.id,
            }, ""

    @api.multi
    def update_vals(self):
        for line in self:
            if not line.order_line_id:
                continue
            order_line = line.order_line_id
            planned = sum(order_line.of_intervention_line_ids
                          .filtered(lambda r: r.intervention_id.state not in ('cancel', 'postponed')
                                              and r.id != line.id)
                          .mapped('qty'))
            qty = order_line.product_uom_qty - planned
            line.update({
                'order_line_id'  : order_line.id,
                'product_id'     : order_line.product_id.id,
                'qty'            : qty,
                'price_unit'     : order_line.price_unit,
                'name'           : order_line.name,
                'taxe_ids'       : [(5, )] + [(4, tax.id) for tax in order_line.tax_id]
                })


class ResPartner(models.Model):
    _inherit = "res.partner"

    intervention_partner_ids = fields.One2many(
        'of.planning.intervention', string="Interventions client", compute="_compute_interventions")
    intervention_address_ids = fields.One2many(
        'of.planning.intervention', string="Interventions adresse", compute="_compute_interventions")
    intervention_ids = fields.Many2many('of.planning.intervention', string=u"Interventions", compute="_compute_interventions")
    intervention_count = fields.Integer(string="Nb d'interventions", compute='_compute_interventions')

    @api.multi
    def _compute_interventions(self):
        interv_obj = self.sudo().env['of.planning.intervention']
        for partner in self:
            partner.intervention_partner_ids = interv_obj.search([('partner_id', '=', partner.id)])
            partner.intervention_address_ids = interv_obj.search([('address_id', '=', partner.id)])
            intervention_ids = interv_obj.search([
                '|',
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

        action['domain'] = ['|', ('partner_id', 'child_of', self.ids), ('partner_id', 'child_of', self.ids)]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            action['context'] = self._get_action_view_intervention_context(context)

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
            context = safe_eval(action['context'])
            context.update({
                'default_address_id': self.partner_shipping_id.id or False,
                'default_order_id': self.id,
            })
            if self.intervention_ids:
                context['force_date_start'] = self.intervention_ids[-1].date_date
                context['search_default_order_id'] = self.id
            action['context'] = str(context)
        return action

    def fiche_intervention_cacher_montant(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'fiche_intervention_cacher_montant')


class OfPlanningInterventionTemplate(models.Model):
    _name = 'of.planning.intervention.template'

    name = fields.Char(string=u"Nom du modèle", required=True)
    active = fields.Boolean(string="Active", default=True)
    code = fields.Char(string="Code", compute="_compute_code", inverse="_inverse_code", store=True, required=True)
    sequence_id = fields.Many2one('ir.sequence', string=u"Séquence", readonly=True)
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche")
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale", company_dependent=True)
    line_ids = fields.One2many('of.planning.intervention.template.line', 'template_id', string="Lignes de facturation")
    product_ids = fields.Many2many('product.product')

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


class OfPlanningInterventionTemplateLine(models.Model):
    _name = 'of.planning.intervention.template.line'

    template_id = fields.Many2one('of.planning.intervention.template', string=u"Modèle", required=True)
    product_id = fields.Many2one('product.product', string='Article')
    price_unit = fields.Float(string='Prix unitaire', digits=dp.get_precision('Product Price'), default=0.0)
    qty = fields.Float(string=u'Qté', digits=dp.get_precision('Product Unit of Measure'))
    name = fields.Text(string='Description')

    @api.onchange('product_id')
    def _onchange_product(self):
        product = self.product_id
        self.qty = 1
        self.price_unit = product.lst_price
        if product:
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
        else:
            self.name = ''

    @api.multi
    def get_intervention_line_values(self):
        self.ensure_one()
        return {
            'product_id': self.product_id,
            'price_unit': self.price_unit,
            'qty': self.qty,
            'name': self.name,
            }


class OfPlanningTag(models.Model):
    _description = u"Étiquettes d'intervention"
    _name = 'of.planning.tag'

    name = fields.Char(string="Nom", required=True, translate=True)
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
    of_qty_planifiee = fields.Float(string=u"Qté(s) réalisée(s)", compute="_compute_of_qty_planifiee", store=True)
    of_intervention_state = fields.Selection([
            ('todo', u'À planifier'),
            ('confirm', u'Planifée'),
            ('done', u'Réalisée'),
            ], string=u"État de planification", compute="_compute_intervention_state", store=True)

    @api.depends('of_intervention_line_ids', 'of_intervention_line_ids.qty', 'of_intervention_line_ids.intervention_state')
    def _compute_of_qty_planifiee(self):
        for line in self:
            lines = line.of_intervention_line_ids.filtered(lambda l: l.intervention_state in ('done', ))
            line.of_qty_planifiee = sum(lines.mapped('qty'))

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

    of_intervention_ids = fields.One2many(
        comodel_name='of.planning.intervention', inverse_name='picking_id', string=u"RDVs d'intervention liés")
    of_intervention_count = fields.Integer(
        string=u"Nb de RDVs d'intervention liés", compute='_compute_of_intervention_count')

    @api.multi
    def _compute_of_intervention_count(self):
        for picking in self:
            picking.of_intervention_count = len(picking.of_intervention_ids)

    @api.multi
    def action_view_interventions(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            order = self.move_lines.mapped('procurement_id').mapped('sale_line_id').mapped('order_id')
            if order and len(order) > 1:
                order = order[0]
            context.update({
                'default_address_id': self.partner_id and self.partner_id.id or False,
                'default_order_id': order and order.id or False,
                'default_picking_id': self.id,
            })
            if self.of_intervention_ids:
                context['force_date_start'] = self.of_intervention_ids[-1].date_date
                context['search_default_picking_id'] = self.id
            action['context'] = str(context)
        return action


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
