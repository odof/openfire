# -*- encoding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import math
from datetime import date
from dateutil.relativedelta import relativedelta
import odoo.addons.decimal_precision as dp
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools import float_compare
from odoo.tools.safe_eval import safe_eval
from odoo.addons.of_utils.models.of_utils import se_chevauchent
from odoo.addons.of_utils.models.of_utils import format_date


class OfService(models.Model):
    _name = "of.service"
    _inherit = ["of.map.view.mixin", "mail.thread"]
    _description = "Demande d'intervention"

    # Init

    @api.model_cr_context
    def _auto_init(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_service'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_self.latest_version
            if version < '10.0.2':
                # à partir de cette version, le champ company_id est obligatoire,
                # on veut donc le remplir partout ou c'est possible
                cr = self.env.cr
                cr.execute("""
-- update DI qui ont un RDV
UPDATE of_service os
SET company_id = opi.company_id
FROM of_planning_intervention opi
WHERE os.id = opi.service_id AND os.company_id IS NULL;

-- update DI qui ont une commande
UPDATE of_service os
SET company_id = so.company_id
FROM sale_order so
WHERE os.order_id = so.id AND os.company_id IS NULL AND so.company_id IS NOT NULL;

-- update DI dont l'adresse a une société
UPDATE of_service os
SET company_id = rp.company_id
FROM res_partner rp
WHERE os.address_id = rp.id AND os.company_id IS NULL AND rp.company_id IS NOT NULL;

-- update DI dont le partenaire a une société
UPDATE of_service os
SET company_id = rp.company_id
FROM res_partner rp
WHERE os.partner_id = rp.id AND os.company_id IS NULL AND rp.company_id IS NOT NULL;
                        """)

        cr = self._cr
        # Lors de la 1ère mise à jour après la refonte des planning (sept. 2019), on migre les données existantes.
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'of_service' AND column_name = 'recurrence'")
        existe_avant = bool(cr.fetchall())

        res = super(OfService, self)._auto_init()

        # Interdiction pour les interventions d'avoir une durée nulle: on passe la durée à 1 et l'état à 'annulé'
        # on pourra supprimer ce code une fois que toutes les bases seront passées en branche planning
        # en pensant bien à le répercuter sur of_migration ;) ;)
        cr.execute("UPDATE of_service SET duree = 1, base_state = 'cancel' "
                   "WHERE duree = 0")

        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'of_service' AND column_name = 'recurrence'")
        existe_apres = bool(cr.fetchall())
        # Si le champ recurrence n'existe pas avant et l'est après la mise à jour,
        # c'est qu'on est à la 1ère mise à jour après la refonte du planning, on doit faire la migration des données.
        if not existe_avant and existe_apres:
            # On peuple le champ durée des services avec la durée de la tâche associée au service.
            cr.execute("UPDATE of_service "
                       "SET duree = of_planning_tache.duree "
                       "FROM of_planning_tache "
                       "WHERE of_service.tache_id = of_planning_tache.id")
            # On met le champ base_state à "calculated" quand state est différent de "cancel".
            cr.execute("UPDATE of_service SET base_state = 'calculated'")

            # On demande la mise à jour du champ date_next des services
            # On supprime la clé 'of_service_compute_date_next' potentiellement déjà existante
            cr.execute("DELETE FROM ir_config_parameter "
                       "WHERE key = 'of_service_compute_date_next'")
            cr.execute("INSERT INTO ir_config_parameter(key,value) "
                       "VALUES ('of_service_compute_date_next', 'init_date_fin_contrat')")
        return res

    @api.model
    def function_set_date_next(self):
        cr = self._cr
        cr.execute("SELECT value FROM ir_config_parameter WHERE key = 'of_service_compute_date_next'")
        values = cr.fetchall()
        if values:
            all_services = self.search([])
            cr.execute("DELETE FROM ir_config_parameter WHERE key = 'of_service_compute_date_next'")

            # lors du passage au nouveau planning, il faut initialiser le champ date_fin_contrat
            if values[0][0] == 'init_date_fin_contrat':
                # On peuple le champ date_fin_contrat des services recurrents avec le champ date_fin
                cr.execute("UPDATE of_service "
                           "SET date_fin_contrat = date_fin "
                           "WHERE recurrence = 't'")
        else:
            cr.execute("SELECT id FROM of_service WHERE date_fin IS NULL or date_next > date_fin LIMIT 1")
            rows = cr.fetchall()
            if not rows:
                # Tout est en ordre, pas d'incohérence dans les dates
                return
            all_services = self.browse([r[0] for r in rows])

        services_avec_last = all_services.filtered(
            lambda s: (s.recurrence
                       and s.date_last
                       and (not s.date_next
                            or s.date_last >= s.date_next)))
        for service in services_avec_last:
            date_next = service.get_next_date(service.date_last)
            cr.execute("UPDATE of_service "
                       "SET date_fin = (%s::date + interval '1 month' - interval '1 day'), "
                       "    date_next = %s "
                       "WHERE id = %s", (date_next, date_next, service.id))

        service_incoherence = all_services.filtered(lambda s: s.date_next > s.date_fin)
        for service in service_incoherence:
            cr.execute("UPDATE of_service "
                       "SET date_fin = (%s::date + interval '1 month' - interval '1 day')"
                       "WHERE id = %s", (service.date_next, service.id))

        # with_context pour bien récupérer les données en DB
        all_services.with_context(vide_cache=True)._compute_state_poncrec()

    @api.model
    def _init_number(self):
        """
        Màj T2427 : ajout du champ number dans les DI, initialisation du champ.
        """
        service_obj = self.with_context(active_test=False)
        services = service_obj.search([('base_state', '=', 'calculated'), ('number', '=', False)])
        services._affect_number()

    @api.model
    def _init_type(self):
        service_obj = self.with_context(active_test=False)
        service_obj.search([('type_id', '=', False), ('recurrence', '=', True)]).write(
            {'type_id': self.env.ref('of_service.of_service_type_maintenance').id})
        service_obj.search([('type_id', '=', False), ('recurrence', '=', False)]).write(
            {'type_id': self.env.ref('of_service.of_service_type_installation').id})

    @api.model
    def _domain_employee_ids(self):
        return ['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]

    # Champs

    # Titre
    name = fields.Char(u"Libellé", compute="_compute_name", store=True)
    active = fields.Boolean(string="Active", default=True)
    base_state = fields.Selection(
        [('draft', u'Brouillon'),  # état par défaut
         ('calculated', u'Calculé'),  # équivalent a state=False mais utile en XML
         ('cancel', u'Annulé')],  # manuellement décidé,
        u"État de calcul", default="draft", required=True, copy=False)
    state = fields.Selection(
        [('draft', u'Brouillon'),  # état par défaut
         ('to_plan', u'À planifier prochainement'),  # prochaine intervention dans moins d'un mois
         ('planned', u'Planifiée récemment'),  # dernière intervention il y a moins d'un mois
         ('planned_soon', u'Planifiée prochainement'),  # planifié pour dans moins d'un mois
         ('progress', u'En cours'),  # par défaut
         ('late', u'En retard de planification'),  # date de prochaine planification il y a plus d'un mois
         # date de fin <= date du jour || de prochaine planif (rec)
         # // durée restante == 0 et date de fin dépassée (ponc)
         ('done', u'Terminée'),
         ('part_planned', u'Partiellement planifiée'),  # intervention(s) et durée restante supérieure à 0
         ('all_planned', u'Entièrement planifiée'),  # intervention(s) et durée restante == 0
         # l'état 'during' est utilisé dans of_mobile mais doit être ajouté ici,
         # sinon la fonction function_set_date_next plante àla première mise à jour après la migration SAV
         # si au moins un RDV est à l'état 'during' et a un RDV
         ('during', u"RDV en cours"),
         ('cancel', u'Annulée')],  # manuellement décidé
        u'État de planification', compute="_compute_state_poncrec", store=True)
    state_ponc = fields.Selection(
        [('draft', u'Brouillon'),  # état par défaut
         ('to_plan', u'À planifier'),  # pas d'intervention
         ('part_planned', u'Partiellement planifiée'),  # intervention(s) et durée restante supérieure à 0
         ('all_planned', u'Entièrement planifiée'),  # intervention(s) et durée restante == 0
         ('late', u'En retard de planification'),  # date de prochaine planification il y a plus d'un mois
         ('done', u'Fait'),  # intervention(s) et durée restante == 0 et date de fin dépassée
         ('during', u"RDV en cours"),
         ('cancel', u'Annulée')],  # manuellement décidé
        u'État', compute='_compute_state_poncrec', store=True)
    intervention_ids = fields.One2many('of.planning.intervention', 'service_id', string="RDVs Tech")
    intervention_count = fields.Integer(string='Nombre de RDVs', compute='_compute_intervention_count')

    # Rubrique Références
    partner_id = fields.Many2one('res.partner', string='Partenaire', required=True, ondelete='restrict')
    address_id = fields.Many2one('res.partner', string=u"Adresse d'intervention", ondelete='restrict')
    address_address = fields.Char('Adresse', related='address_id.contact_address', readonly=True)
    address_street = fields.Char(related='address_id.street', string=u"Rue", readonly=1)
    address_street2 = fields.Char(related='address_id.street2', string=u"Rue 2", readonly=1)
    address_zip = fields.Char('Code Postal', size=24, related='address_id.zip', oldname="partner_zip", readonly=1)
    address_city = fields.Char('Ville', related='address_id.city', oldname="partner_city", readonly=1)
    address_phone = fields.Char(related='address_id.phone', string=u"Téléphone", readonly=1)
    address_mobile = fields.Char(related='address_id.mobile', string=u"Mobile", readonly=1)
    address_email = fields.Char(related='address_id.email', string=u"Courriel", readonly=1)
    secteur_tech_id = fields.Many2one(
        related='address_id.of_secteur_tech_id', readonly=True, store=True)
    department_id = fields.Many2one(
        'res.country.department', compute='_compute_department_id', string=u"Département", readonly=True, store=True)
    tag_ids = fields.Many2many(
        string=u"Étiquettes", comodel_name='of.planning.tag', relation='of_service_of_planning_tag_rel',
        column1='service_id', column2='tag_id')
    company_id = fields.Many2one('res.company', string=u"Société", required=True)

    # Rubrique Origine
    origin = fields.Char(string="Origine")
    order_id = fields.Many2one(
        'sale.order', string="Commande client",
        domain="['|', ('partner_id', 'child_of', partner_id), ('partner_id', 'parent_of', partner_id)]")

    # Rubrique Planification
    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    tache_categ_id = fields.Many2one(related="tache_id.tache_categ_id", readonly=True)
    duree = fields.Float(string=u"Durée estimée")
    duree_planif = fields.Float(string=u"Durée planifiée", compute='_compute_durees', store=True)
    duree_restante = fields.Float(string=u"Durée restante", compute='_compute_durees', store=True)
    date_next = fields.Date(
        string="Prochaine planif", help=u"Date à partir de laquelle programmer le prochain RDV", required=True)
    date_next_last = fields.Date('Prochaine planif (svg)', help=u"Champ pour conserver une possibilité de rollback")
    date_fin = fields.Date(
        string=u"Date de fin de planification",
        help=u"Date à partir de laquelle l'intervention devient en retard de planification")
    date_fin_contrat = fields.Date(u"Date de fin de contrat")
    jour_ids = fields.Many2many(
        'of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours',
        default=lambda self: self._default_jours(), help=u"Jours de disponibilité du client.")
    recurrence = fields.Boolean(string=u"Est récurrente", default=False)
    mois_ids = fields.Many2many(
        'of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois',
        help=u"Mois de référence pour la planification.")
    recurring_rule_type = fields.Selection(
        [('monthly', 'Mois'),
         ('yearly', u'Année(s)')],
        string=u'Récurrence', default='yearly',
        help=u"Spécifier l'intervalle pour le calcul automatique de la date de prochaine planification"
             u" dans les interventions.")
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1, help=u"Répéter (Mois/Années)")

    # Rubrique Description
    note = fields.Text('Notes')

    # Alertes
    recurrence_tache = fields.Boolean(related='tache_id.recurrence', string=u"Récurrence tâche", readonly=True)
    alert_dates = fields.Boolean(string=u"Incohérence dans les dates", compute="_compute_alert_dates")

    # Vue Calendar / Planning / Map / Liste
    geo_lat = fields.Float(related='address_id.geo_lat')  # Vue Map
    geo_lng = fields.Float(related='address_id.geo_lng')  # Vue Map
    precision = fields.Selection(related='address_id.precision')  # Vue Map
    partner_name = fields.Char(related='partner_id.name')  # Vue Map
    partner_mobile = fields.Char(related='partner_id.mobile')  # Vue Map
    partner_phone = fields.Char(related='partner_id.phone')  # Vue Map
    tache_name = fields.Char(related="tache_id.name", readonly=True)  # Vue Map
    color = fields.Char(compute='_compute_color', string='Couleur', store=False)  # Vue Map, Liste
    date_last = fields.Date(
        string=u'Dernier RDV', compute='_compute_durees', store=True,
        help=u"Date du dernier RDV en date. Ne prend pas en compte les RDVs annulés ni reportés")  # Vue liste

    # Champs de recherche
    date_fin_min = fields.Date(string=u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date(string=u"Date échéance max", compute='lambda *a, **k:{}')
    date_controle = fields.Date(string=u"Date de contrôle", compute='lambda *a, **k:{}')

    # Nouveaux champs DI

    type_id = fields.Many2one(comodel_name='of.service.type', string="Type", required=True)
    # partner_id.category_id est un M2M
    partner_tag_ids = fields.Many2many(string=u"Étiquettes client", related='partner_id.category_id', readonly=True)

    saleorder_ids = fields.One2many(comodel_name='sale.order', compute='_compute_saleorder_ids', string=u"Ventes")
    invoice_ids = fields.One2many(
        comodel_name='account.invoice', compute='_compute_invoice_ids', string=u"Factures de ventes")
    saleorder_count = fields.Integer(string=u"# Ventes", compute='_compute_saleorder_ids')
    invoice_count = fields.Integer(string=u"# Factures de ventes", compute='_compute_invoice_ids')
    historique_interv_ids = fields.Many2many(
        string=u"Historique des interventions", comodel_name='of.planning.intervention',
        column1='of.service', column2='of.planning.intervention', relation='of_service_historique_interv_rel',
        compute='_compute_historique_interv_ids',
        help=u"Historique des RDVs du parc installé. Si pas de parc installé, historique de l'adresse")
    template_id = fields.Many2one(comodel_name='of.planning.intervention.template', string=u"Modèle d'intervention")
    number = fields.Char(string=u"Numéro", copy=False)
    titre = fields.Char(string=u"Titre")
    priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Normal'),
            ('2', 'High')
        ], string=u"Priorité", index=True, default='0')
    spec_date = fields.Char(string="Date", compute="_compute_spec_date")
    user_id = fields.Many2one(comodel_name='res.users', string="Utilisateur", default=lambda r: r.env.user)
    kanban_step_id = fields.Many2one(
        comodel_name='of.service.stage', string=u"Étape", group_expand='_read_group_stage_ids',
        domain="[('type_ids','=',type_id)]")
    employee_ids = fields.Many2many(
        comodel_name='hr.employee', string="Intervenants", domain=lambda self: self._domain_employee_ids())
    last_attachment_id = fields.Many2one(
        comodel_name='ir.attachment', string=u"Dernier rapport", compute="_compute_last_attachment_id"
    )

    line_ids = fields.One2many(
        comodel_name='of.service.line', inverse_name='service_id', string=u"Lignes de facturation")
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string=u"Position fiscale",
        domain="[('tax_ids.tax_src_id.type_tax_use','=','sale')]")
    currency_id = fields.Many2one(
        comodel_name='res.currency', string=u"Currency", readonly=True, related='company_id.currency_id')

    price_subtotal = fields.Monetary(compute='_compute_amount', string=u"Sous-total HT", readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string=u"Taxes", readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string=u"Sous-total TTC", readonly=True, store=True)

    # Constraints

    @api.constrains('date_next', 'date_fin')
    def check_alert_dates(self):
        for service in self:
            if service.alert_dates:
                raise UserError(_(u'Intervention (%s): Inchohérence dans les dates' % service.name))

    _sql_constraints = [
        ('duree_non_nulle_constraint',
         'CHECK ( duree > 0 )',
         _(u"La durée de l'intervention doit être supérieure à 0!")),
    ]

    # Default

    @api.model
    def _default_company(self):
        # Pour les objets du planning, le choix de société se fait par un paramètre de config
        if self.env['ir.values'].get_default('of.intervention.settings', 'company_choice') == 'user':
            return self.env['res.company']._company_default_get('of.service')
        return False

    def _default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    # Compute/search methods

    @api.multi
    @api.depends('address_id', 'partner_id', 'tache_id')
    def _compute_name(self):
        for service in self:
            partner_name = service.partner_id.name or u''
            address_zip = service.address_id.zip or u''
            tache_name = service.tache_id.name or u''
            service.name = tache_name + " " + partner_name + " " + address_zip

    @api.multi
    @api.depends(
        'date_next', 'date_fin_contrat', 'duree', 'base_state', 'recurrence', 'date_last', 'date_fin', 'duree_restante',
        'intervention_ids', 'intervention_ids.state')
    def _compute_state_poncrec(self):
        for service in self:
            service_state = service.get_state_poncrec_date(fields.Date.context_today(self), to_plan_avance=True)
            if not service.recurrence and service.state_ponc != service_state:
                service.state_ponc = service_state
            if service.state != service_state:
                service.state = service_state

    @api.depends('intervention_ids', 'intervention_ids.state')
    @api.multi
    def _compute_intervention_count(self):
        for service in self:
            service.intervention_count = len(service.intervention_ids.filtered(
                lambda r: r.state not in ('cancel', 'postponed')))

    @api.multi
    @api.depends(
        'duree', 'intervention_ids', 'recurrence', 'intervention_ids.state', 'date_next', 'mois_ids',
        'tache_id', 'tache_id.fourchette_planif')
    def _compute_durees(self):
        for service in self:
            # Dans cette fonction, les affectations sont très coûteuses, car elles impliquent un grand nombre de
            # recalculs. On n'affectera donc les valeurs que si elles diffèrent de ce celle stockée en DB.
            date_last_old = service.date_last
            duree_planif_old = service.duree_planif
            duree_restante_old = service.duree_restante
            # ne pas prendre les interventions annulées / reportées
            plannings = service.intervention_ids.filtered(lambda p: p.state not in ('cancel', 'postponed'))
            date_last = plannings and plannings.sorted('date', reverse=True)[0].date_date or False
            if date_last != date_last_old:
                service.date_last = date_last

            if service.recurrence and service.date_next:
                # On cherche la durée planifiée pour l'occurrence en cours.
                # Il nous faut savoir quelle est l'occurrence en cours
                date_next_ref_str = service.get_date_proche(fields.Date.today())  # début d'occurrence en cours
                date_fin_ref_str = service.get_fin_date(date_next_ref_str)  # fin d'occurrence en cours
                date_next_ref_da = fields.Date.from_string(date_next_ref_str)
                date_fin_ref_da = fields.Date.from_string(date_fin_ref_str)
                # RDVs pris en avance. Récupération de date de fin de l'occurrence précédente pour connaître l'écart
                #   entre les deux et le couper en deux.
                # tous les RDVs de la 1ere moitié sont des RDVs en retard de l'occurrence précédente
                #   et ne sont pas a prendre en compte dans la durée planifiée
                # tous les RDVs de la 2eme moitié sont des RDVs en avance de l'occurrence en cours
                date_next_prec_str = service.get_next_date(date_next_ref_str, forward=False)
                date_fin_prec_str = service.get_fin_date(date_next_prec_str)
                date_prec_da = fields.Date.from_string(date_fin_prec_str)
                diff_prec_td = (date_next_ref_da - date_prec_da) / 2
                date_avance_da = date_next_ref_da - diff_prec_td
                date_avance_str = fields.Date.to_string(date_avance_da)
                # RDVs pris en retard, même principe que pour les RDVs pris en avance
                date_next_suiv_str = service.get_next_date(date_next_ref_str, forward=True)
                date_suiv_da = fields.Date.from_string(date_next_suiv_str)
                diff_suiv_td = (date_suiv_da - date_fin_ref_da) / 2
                date_retard_da = date_next_ref_da + diff_suiv_td
                date_retard_str = fields.Date.to_string(date_retard_da)

                # Sélection des RDVs de l'occurrence en cours
                plannings = plannings.filtered(lambda p: date_avance_str <= p.date_date < date_retard_str)

            duree_planif = sum(plannings.mapped('duree'))
            if float_compare(duree_planif, duree_planif_old, 5):
                service.duree_planif = duree_planif
            duree_restante = service.duree > service.duree_planif and service.duree - service.duree_planif or 0
            if float_compare(duree_restante, duree_restante_old, 5):
                service.duree_restante = duree_restante

    def _search_duree_restante(self, operator, operand):
        services = self.search([])
        res = safe_eval("services.filtered(lambda s: s.duree_restante %s %.2f)" % (operator, operand),
                        {'services': services})
        return [('id', 'in', res.ids)]

    @api.depends('date_next', 'date_fin')
    def _compute_alert_dates(self):
        for service in self:
            service.alert_dates = service.date_next and service.date_fin and service.date_next > service.date_fin

    @api.multi
    @api.depends('state')
    def _compute_color(self):
        u""" COULEURS :
        Gris  : service dont l'adresse n'a pas de coordonnées GPS, ou service inactif
        Orange: service à planifier ou partiellement planifié
        Rouge : service en retard de planification
        Noir  : autres services
        """
        for service in self:
            if service.state in ('planned', 'planned_soon', 'progress', 'done', 'all_planned'):
                service.color = 'black'
            elif service.state in ('to_plan', 'part_planned'):
                service.color = 'orange'
            elif service.state == 'late':
                service.color = 'red'
            else:
                service.color = 'gray'

    @api.model
    def _search_last_date(self, operator, operand):
        cr = self._cr

        query = ("SELECT s.id\n"
                 "FROM of_service AS s\n"
                 "LEFT JOIN of_planning_intervention AS p\n"
                 "  ON p.service_id = s.id\n")

        if operand:
            if len(operand) == 10:
                # Copié depuis osv/expression.py
                if operator in ('>', '<='):
                    operand += ' 23:59:59'
                else:
                    operand += ' 00:00:00'
            query += ("GROUP BY s.id\n"
                      "HAVING MAX(p.date) %s '%s'" % (operator, operand))
        else:
            if operator == '=':
                query += "WHERE p.id IS NULL"
            else:
                query += "WHERE p.id IS NOT NULL"
        cr.execute(query)
        rows = cr.fetchall()
        return [('id', 'in', rows and zip(*rows)[0])]

    @api.depends('line_ids', 'line_ids.saleorder_line_id')
    def _compute_saleorder_ids(self):
        for service in self:
            service.saleorder_ids = service.line_ids.mapped('saleorder_line_id').mapped('order_id')
            service.saleorder_count = len(service.saleorder_ids)

    @api.depends('line_ids', 'line_ids.invoice_line_ids', 'saleorder_ids', 'saleorder_ids.invoice_ids',
                 'line_ids.invoice_line_ids.invoice_id')
    def _compute_invoice_ids(self):
        for service in self:
            invoices = service.line_ids.mapped('invoice_line_ids').mapped('invoice_id')
            invoices |= service.saleorder_ids.mapped('invoice_ids')
            service.invoice_count = len(invoices)
            service.invoice_ids = invoices

    @api.depends('address_id.intervention_address_ids', 'partner_id.intervention_address_ids')
    def _compute_historique_interv_ids(self):
        interv_obj = self.env['of.planning.intervention']
        for service in self:
            partner = service.address_id or service.partner_id
            if partner:
                service.historique_interv_ids = interv_obj.search([('address_id', '=', partner.id)])

    @api.depends()
    def _compute_spec_date(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for service in self:
            interventions = service.intervention_ids.filtered(lambda i: i.state not in ('cancel', 'postponed'))
            if service.state == 'done' and interventions:
                service.spec_date = u"Réalisée le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            elif interventions:
                service.spec_date = u"Prévue le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            else:
                service.spec_date = u"Prévue entre %s et %s" % (
                    format_date(service.date_next, lang), format_date(service.date_fin, lang))

    @api.depends()
    def _compute_last_attachment_id(self):
        """ Récupère le rapport 'Fiche d'intervention' du dernier RDV ayant la fiche d'intervention dans ses PJ"""
        attachment_obj = self.env['ir.attachment']
        for service in self:
            interventions = service.intervention_ids.filtered(lambda i: i.state not in ('cancel', 'postponed'))
            if interventions:
                for i in xrange(1, len(service.intervention_ids) + 1):
                    current_interv = service.intervention_ids[-i]
                    attachment = attachment_obj.search([('res_model', '=', 'of.planning.intervention'),
                                                        ('res_id', '=', current_interv.id),
                                                        ('of_intervention_report', '=', True)])
                    if attachment:
                        service.last_attachment_id = attachment[-1]
                        break

    @api.depends('line_ids', 'line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_amount(self):
        for intervention in self:
            intervention.price_subtotal = sum(intervention.line_ids.mapped('price_subtotal'))
            intervention.price_tax = sum(intervention.line_ids.mapped('price_tax'))
            intervention.price_total = sum(intervention.line_ids.mapped('price_total'))

    @api.depends('partner_id.department_id', 'address_id.department_id')
    def _compute_department_id(self):
        for record in self:
            if record.address_id:
                record.department_id = record.address_id.department_id
            elif record.partner_id:
                record.department_id = record.partner_id.department_id

    # @api.onchange

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.ensure_one()
        if self.partner_id and not self.address_id:
            addresses = self.partner_id.address_get(['delivery'])
            self.address_id = addresses['delivery']

    @api.onchange('address_id')
    def _onchange_address_id(self):
        self.ensure_one()
        if self.address_id:
            # Pour les objets du planning, le choix de la société se fait par un paramètre de config
            company_choice = self.env['ir.values'].get_default(
                'of.intervention.settings', 'company_choice') or 'contact'
            if company_choice == 'contact' and self.address_id.company_id:
                self.company_id = self.address_id.company_id.id
            elif company_choice == 'contact' and self.partner_id.company_id:
                self.company_id = self.partner_id.company_id.id
            # en mode contact avec un contact sans société, ou en mode user
            else:
                self.company_id = self.env.user.company_id
            if not self.partner_id:
                address = self.address_id
                if address.parent_id:
                    address = address.parent_id
                invoice_address_id = address.address_get(['invoice'])['invoice']
                self.partner_id = invoice_address_id

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        self.ensure_one()
        if self.tache_id:
            if self.tache_id.recurrence == self.recurrence:
                self.recurring_rule_type = self.tache_id.recurring_rule_type
                self.recurring_interval = self.tache_id.recurring_interval
            if self.tache_id.fiscal_position_id and not self.fiscal_position_id:
                self.fiscal_position_id = self.tache_id.fiscal_position_id
            # ne pas créer de ligne si la tache a été affecté via le template
            if self.tache_id.product_id and (not self.template_id or self.template_id.tache_id != self.tache_id):
                new_line = self.env['of.service.line'].new({
                    'service_id': self.id,
                    'product_id': self.tache_id.product_id.id,
                    'qty': 1,
                    'price_unit': self.tache_id.product_id.lst_price,
                    'name': self.tache_id.product_id.name,
                })
                self.line_ids |= new_line
                self.line_ids.compute_taxes()
            if not self.duree:
                self.duree = self.tache_id.duree
        self.date_fin = self.get_fin_date()

    @api.onchange('date_next')
    def _onchange_date_next(self):
        # Remplissage automatique du mois en fonction de la date de prochaine intervention choisie
        # /!\ Un simple clic sur le champ date appelle cette fonction, et génère le mois avec la date courante
        #       avant que l'utilisateur ait confirmé son choix.
        #     Cette fonction doit donc être autorisée à écraser le mois déjà saisi
        #     Pour éviter les ennuis, elle est donc restreinte à un usage en mode création de nouveau service uniquement
        if self.date_next and (not hasattr(self, '_origin') or not self._origin):  # <- signifie mode creation
            mois = self.env['of.mois'].search([('numero', '=', int(self.date_next[5:7]))])
            mois_id = mois[0] and mois[0].id or False
            if mois_id:
                self.mois_ids = [(4, mois_id, 0)]
        if self.date_next:
            self.date_fin = self.get_fin_date()

    @api.onchange('template_id')
    def onchange_template_id(self):
        service_line_obj = self.env['of.service.line']
        template = self.template_id
        if self.base_state == "draft" and template:
            if template.tache_id:
                self.tache_id = template.tache_id
            if template.type_id:
                self.type_id = template.type_id
            if not self.fiscal_position_id:
                self.fiscal_position_id = template.fiscal_position_id
            new_lines = self.line_ids
            for line in template.line_ids:
                data = line.get_intervention_line_values()
                data['service_id'] = self.id
                new_lines += service_line_obj.new(data)
            new_lines.compute_taxes()
            self.line_ids = new_lines

    @api.onchange('type_id')
    def onchange_type_id(self):
        if self.type_id and self.type_id.kanban_ids:
            self.kanban_step_id = self.type_id.kanban_ids[0]

    @api.onchange('fiscal_position_id')
    def onchange_fiscal_position_id(self):
        if self.fiscal_position_id:
            self.line_ids.compute_taxes()

    # CRUD

    @api.model
    def create(self, vals):
        if vals.get('address_id') and not vals.get('partner_id'):
            address = self.env['res.partner'].browse(vals['address_id'])
            partner = address.parent_id or address
            vals['partner_id'] = partner.id
        return super(OfService, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(OfService, self).write(vals)
        if vals.get('base_state') == 'calculated':
            self._affect_number()
        return res

    # Héritages

    @api.model
    def get_color_map(self):
        u"""
        fonction pour la légende de la vue map
        """
        title = "Prochaine Planification"
        v0 = {'label': u"Planifié", 'value': 'black'}
        v1 = {'label': u'À planifier', 'value': 'orange'}
        v2 = {'label': u'En retard', 'value': 'red'}
        return {"title": title, "values": (v0, v1, v2)}

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        res = stages.search([], order=order)
        if self._context.get('of_kanban_steps') == 'Maintenance':
            ce_type = self.env.ref('of_service.of_service_type_maintenance', raise_if_not_found=False)
            if ce_type:
                return res.filtered(lambda s: ce_type.id in s.type_ids.ids)
        return res

    @api.multi
    def create_invoice(self):
        invoice_obj = self.env['account.invoice']

        msgs = []
        for service in self:
            # toutes les lignes sont liées à une commande (au moins une avec commande et aucune sans commande)
            if not service.line_ids.filtered(lambda l: not l.invoice_line_ids):
                msgs.append(u"Les lignes facturables de la demande d'intervention %s étant liées à des lignes de "
                            u" commandes, veuillez effectuer la facturation depuis le bon de commande." % service.name)
                continue
            invoice_data, msg = service._prepare_invoice()
            msgs.append(msg)
            if invoice_data:
                invoice = invoice_obj.create(invoice_data)
                invoice.compute_taxes()
                invoice.message_post_with_view('mail.message_origin_link',
                                               values={'self': invoice, 'origin': service},
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

    # Actions

    @api.multi
    def action_view_intervention(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]

        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            action['context'] = self.get_action_view_intervention_context(context)
        action = self.mapped('intervention_ids').get_action_views(self, action)
        return action

    @api.multi
    def action_view_saleorder(self):
        if self.ensure_one():
            return {
                'name': u"Commandes client",
                'view_mode': 'tree,kanban,form',
                'res_model': 'sale.order',
                'res_id': self.saleorder_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.saleorder_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_invoice(self):
        invoices = self.invoice_ids
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
    def action_service_send(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'of.service',
            'default_res_id': self.ids[0],
            'default_composition_mode': 'comment'
        })
        try:
            # ajouter le modèle d'email
            template_id = self.env.ref('of_service.email_template_of_service').id
            ctx['default_template_id'] = template_id
            ctx['default_use_template'] = bool(template_id)
        except ValueError:
            pass
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
    def _prepare_sale_order_values(self):
        self.ensure_one()
        Sale = self.env['sale.order']
        # utilisation de new() pour trigger les onchanges facilement
        sale_order_new = Sale.new({
            'partner_id': self.partner_id.id,
            'origin': self.number,
        })
        sale_order_new.onchange_partner_id()
        sale_order_new.update({'fiscal_position_id': self.fiscal_position_id.id})
        return sale_order_new._convert_to_write(sale_order_new._cache)

    @api.multi
    def make_sale_order(self):
        self.ensure_one()

        Sale = self.env['sale.order']
        SaleLine = self.env['sale.order.line']

        # Ne pas créer de commande si la DI n'est pas validée
        if self.base_state != 'calculated':
            return self.env['of.popup.wizard'].popup_return(
                message=u"Cette demande d'intervention n'est pas validée.")

        # Ne pas créer de commande si pas de lignes
        if not self.line_ids:
            return self.env['of.popup.wizard'].popup_return(
                message=u"Cette demande d'intervention n'a aucune ligne.")

        # Ne pas créer de commande si toutes les lignes sont déjà associées à une commande
        if not self.line_ids.filtered(lambda l: not l.saleorder_line_id):
            return self.env['of.popup.wizard'].popup_return(
                message=u"Toutes les lignes sont déjà associées à une commande de vente.")

        # Ne pas créer de commande si toutes les lignes sont déjà associées à une ou des factures
        if not self.line_ids.filtered(lambda l: not l.invoice_line_ids):
            return self.env['of.popup.wizard'].popup_return(
                message=u"Toutes les lignes sont déjà associées à une ou plusieurs factures.")

        # Ne pas créer de commande si la position fiscale n'est pas renseignée
        if not self.fiscal_position_id:
            return self.env['of.popup.wizard'].popup_return(
                message=u"Veuillez renseigner une position fiscale.")

        res = {
            'name': u"Devis",
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        order_values = self._prepare_sale_order_values()
        sale_order = Sale.create(order_values)
        lines_to_create = []
        # Récupération des lignes de commandes
        for line in self.orderable_lines():
            line_vals = line.prepare_so_line_vals(sale_order)
            lines_to_create.append((0, 0, line_vals))
        sale_order.write({'order_line': lines_to_create})
        # Connecter les lignes à leur ligne de commande correspondante
        for line in self.line_ids.filtered(lambda l: not l.saleorder_line_id and not l.invoice_line_ids):
            line.saleorder_line_id = SaleLine.search([('of_service_line_id', '=', line.id)], limit=1)
        # Renvoyer la commande créée
        res['res_id'] = sale_order.id

        return res

    @api.multi
    def orderable_lines(self):
        """ Fonction à surcharger si on veut retirer des lignes lors de la création de commande"""
        self.ensure_one()
        return self.line_ids.filtered(lambda l: not l.saleorder_line_id and not l.invoice_line_ids)

    @api.multi
    def _get_invoicing_company(self, partner):
        return self.company_id or partner.company_id

    @api.multi
    def _prepare_invoice_lines(self):
        self.ensure_one()
        lines_data = []
        error = ''
        for line in self.line_ids.filtered(
                lambda l: not l.saleorder_line_id and not l.invoice_line_ids):
            line_data, line_error = line._prepare_invoice_line()
            lines_data.append((0, 0, line_data))
            error += line_error
        return lines_data, error

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()

        msg_succes = u"SUCCÈS : création de la facture depuis la demande d'intervention %s"
        msg_erreur = u"ÉCHEC : création de la facture depuis la demande d'intervention %s : %s"

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
            'origin': self.number or u"Demande d'Intervention",
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

    @api.multi
    def button_open_of_planning_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        interventions = self.intervention_ids
        if len(interventions) > 1:
            action['context'] = {'search_default_service_id': self.id}
        elif len(interventions) == 1:
            action['views'] = [(self.env.ref('of_planning.of_planning_intervention_view_form').id, 'form')]
            action['res_id'] = interventions.ids[0]
        else:
            action = self.env['of.popup.wizard'].popup_return(message=u"Aucun RDV d'intervention lié.")
        return action

    @api.multi
    def print_intervention_report(self):
        if self.intervention_ids:
            return self.env['report'].get_action(
                self.intervention_ids, 'of_planning.of_planning_fiche_intervention_report_template')
        else:
            return self.env['of.popup.wizard'].popup_return(message=u"Aucun RDV d'intervention lié.")

    @api.multi
    def button_valider(self):
        # laisser le système calculer l'état
        return self.write({'base_state': 'calculated'})

    @api.multi
    def button_annuler(self):
        return self.write({'base_state': 'cancel'})

    @api.multi
    def button_brouillon(self):
        return self.write({'base_state': 'draft'})

    # Autres

    @api.model
    def compute_state_poncrec_daily(self):
        """
        Force le recalcul de l'état des demandes d'intervention.
        Est lancé tous les matins, pour que le changement de date du jour soit pris en compte.
        """
        self.search([('base_state', '=', False)]).write({'base_state': 'calculated'})
        self.search([('base_state', '=', 'calculated'), ('recurrence', '=', True)])._compute_durees()
        self.search([('base_state', '=', 'calculated')])._compute_state_poncrec()

    @api.multi
    def filter_state_poncrec_date(self, date_eval=fields.Date.today(), state_list=('to_plan', 'part_planned', 'late')):
        """
        Permet de filtrer les interventions du self à une date donnée
        :param date_eval: Date à laquelle on veut connaitre l'état des interventions
        :param state_list: Liste des états autorisés par le filtre
        :return: env['of.service'] contenant les interventions filtrées
        """
        services_pass = self.env['of.service']
        for service in self:
            service_state = service.get_state_poncrec_date(date_eval=date_eval, to_plan_avance=False)
            if service_state in state_list:
                services_pass |= service
        return services_pass

    @api.multi
    def get_state_poncrec_date(self, date_eval=fields.Date.today(), to_plan_avance=False):
        """
        Calcule l'état d'une intervention à une date donnée, est prévu pour être utilisé pour des dates futures
        (en raison du champ duree_restante)
        On pourra créer une fonction get_durees_date pour faire fonctionner get_state_poncrec_date dans le passé
        :param date_eval: Date à laquelle on veut connaître l'état des interventions
        :param to_plan_avance: True pour considérer qu'une intervention est à 'to_plan' 1 mois avant sa date_next
        :return: État de l'intervention à la date donnée
        """
        self.ensure_one()
        un_mois = relativedelta(months=1)
        date_eval_da = fields.Date.from_string(date_eval)
        il_y_a_un_mois_da = date_eval_da - un_mois
        dans_un_mois_da = date_eval_da + un_mois
        fin_to_plan_da = to_plan_avance and dans_un_mois_da or date_eval_da
        # les états 'annulé' et 'brouillon' sont provoqués manuellement
        # le champ 'date_next' correspond à la date de début de la fourchette de planification
        # et le champ 'date_fin' à la date de fin de la fourchette de planification
        if self.base_state and self.base_state == 'calculated':
            date_next_da = fields.Date.from_string(self.date_next)
            date_last_da = self.date_last and fields.Date.from_string(self.date_last) or False
            date_fin_da = self.date_fin and fields.Date.from_string(self.date_fin) \
                or date_next_da + relativedelta(days=13)
            if self.recurrence:
                fin_contrat_da = self.date_fin_contrat and fields.Date.from_string(self.date_fin_contrat) or False
                # le service expire avant la date donnée ou avant la date de prochaine planif: terminé
                if fin_contrat_da and (fin_contrat_da < date_next_da or fin_contrat_da < date_eval_da):
                    service_state = 'done'
                # chevauchement de la fourchette de planif de l'intervention et la ou les dates d'évaluations
                # et pas de dernier RDV ou dernier RDV plus d'un mois avant: à planifier
                elif se_chevauchent(date_next_da, date_fin_da, date_eval_da, fin_to_plan_da, strict=False) and \
                        (not date_last_da or date_last_da < il_y_a_un_mois_da):
                    service_state = 'to_plan'
                # dernier RDV moins d'un mois avant: planifié récemment
                elif date_last_da and (il_y_a_un_mois_da <= date_last_da <= date_eval_da):
                    service_state = 'planned'
                # dernier RDV moins d'un mois après: planifié prochainement
                elif date_last_da and (date_eval_da < date_last_da <= dans_un_mois_da):
                    service_state = 'planned_soon'
                # fin de prochaine planification avant la date donnée: en retard
                elif date_fin_da < date_eval_da:
                    service_state = 'late'
                else:  # par défaut
                    service_state = 'progress'
            else:
                # la durée restante n'est pas nulle et la date de fin est dépassée: en retard
                if date_fin_da < date_eval_da and self.duree_restante != 0:
                    service_state = 'late'
                elif not date_last_da:  # aucun RDV planifié
                    service_state = 'to_plan'
                # durée restant == 0 et le dernier RDV planifié est passé: fait
                elif self.duree_restante == 0 and date_last_da < date_eval_da:
                    service_state = 'done'
                # durée restante == 0 et le dernier RDV planifié est futur: entièrement planifié
                elif self.duree_restante == 0 and self.duree:
                    service_state = 'all_planned'
                else:  # la durée restante n'est pas nulle et la date de fin est future
                    service_state = 'part_planned'
        else:
            service_state = self.base_state
        return service_state

    @api.multi
    def get_date_proche(self, date_eval, return_string=True):
        """
        Retrouve l'occurrence la plus proche de la date étudiée, dans le passé ou le futur
        :param date_eval: Date à placer sur un mois autorisé
        :param return_string: Vrai si date à retourner en String, Faux en Date
        :return: date de début de fourchette de planif de l'occurence la plus proche
        :rtype string ou Date
        """
        self.ensure_one()
        if not self.recurrence:
            return
        mois_ints = self.mois_ids.mapped('numero') or range(1, 13)
        if isinstance(date_eval, basestring):
            date_eval_da = fields.Date.from_string(date_eval)
        else:
            date_eval_da = date_eval
        date_eval_mois_int = date_eval_da.month
        if date_eval_mois_int in mois_ints:  # la date est déjà sur un mois autorisé
            if return_string:
                return fields.Date.to_string(date(year=date_eval_da.year, month=date_eval_mois_int, day=1))
            return date(year=date_eval_da.year, month=date_eval_mois_int, day=1)
        mois_courant_int = date_eval_mois_int

        # Détection du mois précédent et du mois suivant dans le service (valeur 1-12)
        mois_passe_int = mois_ints[-1]
        mois_futur_int = mois_ints[0]
        for mois_int in mois_ints:
            if mois_int < mois_courant_int:
                mois_passe_int = mois_int
            else:
                mois_futur_int = mois_int
                break

        # Modification des mois : valeur de -11 à + 24 selon l'année
        if mois_passe_int > date_eval_mois_int:
            mois_passe_int -= 12
        if mois_futur_int < date_eval_mois_int:
            mois_futur_int += 12
        # Mois le plus proche de la date fournie
        mois_int = mois_passe_int if mois_passe_int + mois_futur_int > 2 * date_eval_mois_int else mois_futur_int
        mois_int -= 1

        # A ce stade, mois_int est un numéro de mois de 0 à 11
        #   auquel a été ajouté/retiré 12 en fonction de l'année
        # Il ne reste donc plus qu'à calculer l'année et le mois réels
        annee_int = date_eval_da.year + int(math.floor(mois_int / 12.0))
        mois_int = mois_int % 12 + 1
        # victoire! la date étudiée est bien placée sur un mois autorisé
        date_eval_da = date(annee_int, mois_int, 1)
        if return_string:
            return fields.Date.to_string(date_eval_da)
        return date_eval_da

    @api.multi
    def get_next_date(self, date_str, forward=True):
        """
        Retrouve la date de prochaine planif de l'occurence suivante/précédente suivant le mode
        :param date_str: Date de l'occurrence à étudier
        :param forward: chercher la prochaine si True, la dernière sinon
        :return: date de début de fourchette de planif de l'occurence suivante/précédente
        :rtype string
        """
        self.ensure_one()
        if self.recurrence:
            mois_ints = self.mois_ids.mapped('numero') or range(1, 13)

            if forward:
                # si mode forward, l'occurence par défaut à étudier est dernière
                date_from_da = fields.Date.from_string(max(date_str, self.date_last))
            else:
                # si mode backward, l'occurence par défaut à étudier est la prochaine
                date_from_da = fields.Date.from_string(min(date_str, self.date_next))

            if not date_from_da:
                raise UserError(u"get_date_next: date de référence manquante")

            date_from_da = self.get_date_proche(date_from_da, return_string=False)

            if forward:
                date_to_da = date_from_da + self.get_relative_delta(self.recurring_rule_type, self.recurring_interval)
                date_to_mois_int = date_to_da.month
                # générer les mois de l'année suivante pour faciliter calcul du mois et de l'année du résultat
                mois_int_temp = mois_ints + [m + 12 for m in mois_ints]
                res_mois_int = min(mois_int_temp, key=lambda mois: (abs(mois - date_to_mois_int), mois))
                if res_mois_int > 12:
                    res_next_year = True
                    res_mois_int -= 12
                else:
                    res_next_year = False
                res_year_int = date_to_da.year + res_next_year
            else:
                date_to_da = date_from_da - self.get_relative_delta(self.recurring_rule_type, self.recurring_interval)
                date_to_mois_int = date_to_da.month
                # générer les mois de l'année précédente pour faciliter calcul du mois et de l'année du résultat
                mois_int_temp = mois_ints + [m - 12 for m in mois_ints]
                res_mois_int = min(mois_int_temp, key=lambda mois: (abs(mois - date_to_mois_int), mois))
                if res_mois_int < 1:
                    res_last_year = True
                    res_mois_int += 12
                else:
                    res_last_year = False
                res_year_int = date_to_da.year - res_last_year

            return fields.Date.to_string(date(year=res_year_int, month=res_mois_int, day=1))
        else:
            return False

    @api.multi
    def get_fin_date(self, date_str=False):
        """
        :param date_str: Date de prochaine planif à utiliser pour le calcul, sous format string
        :return: Date à partir de laquelle l'intervention passe à l'état 'en retard'
        :rtype string
        """
        self.ensure_one()
        date_next_str = date_str or self.date_next or False
        if date_next_str:
            date_fin = fields.Date.from_string(date_next_str)

            if self.tache_id and self.tache_id.fourchette_planif:
                # tache présente avec une granularité de planif
                if self.tache_id.fourchette_planif == 'semaine':
                    date_fin += relativedelta(weeks=1)
                elif self.tache_id.fourchette_planif == 'quinzaine':
                    date_fin += relativedelta(weeks=2)
                elif self.tache_id.fourchette_planif == 'mois':
                    date_fin += relativedelta(months=1)
            else:
                # tache non présente ou sans granularité
                if self.recurrence:
                    # un mois par défaut pour les ramonages et entretiens
                    date_fin += relativedelta(months=1)
                else:
                    # 2 semaines par défaut
                    date_fin += relativedelta(weeks=2)
            date_fin -= relativedelta(days=1)
            # ^- moins 1 jour car les intervalles de dates sont inclusifs
            return fields.Date.to_string(date_fin)
        else:
            return ""

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval, day=1)  # 1er du mois
        else:
            return relativedelta(years=interval, day=1)  # 1er du mois

    @api.multi
    def get_action_view_intervention_context(self, action_context=None):
        if action_context is None:
            action_context = {}
        action_context.update({
            'default_partner_id': self.partner_id.id,
            'default_address_id': self.address_id and self.address_id.id or self.partner_id.id,
            'default_tache_id': self.tache_id and self.tache_id.id or False,
            'default_duree': self.duree,
            'default_tag_ids': [(6, 0, [tag.id for tag in self.tag_ids])],
            'default_description_interne': self.note,
            'default_service_id': self.id,
            'create': self.base_state == 'calculated',
            'edit': self.base_state == 'calculated',
            'default_order_id': self.order_id and self.order_id.id or False,
            'default_fiscal_position_id': self.fiscal_position_id and self.fiscal_position_id.id or False,
            'default_template_id': self.template_id and self.template_id.id or False,
            'default_employee_ids': [(6, 0, [emp.id for emp in self.employee_ids])],
        })
        if self.intervention_ids:
            action_context['force_date_start'] = self.intervention_ids[-1].date_date
            action_context['search_default_service_id'] = self.id
        elif self.base_state != 'calculated' or self.state == 'done':
            # inhiber la création en vue calendrier si l'intervention n'est pas planifiable
            # (brouillon, annulée, terminée)
            action_context['inhiber_create'] = True
            if self.state == 'done':
                param = u"terminée"
            else:
                param = self.base_state == 'cancel' and u"annulée" or u"qui n'est pas validée"
            action_context['inhiber_message'] = u"Vous ne pouvez pas créer de RDV pour une intervention %s." % param
        if self.line_ids:
            # Générer les lignes ici ne fonctionnait pas, on signale donc dans le contexte qu'il faudra les générer.
            # Elles seront ensuite générées dans le onchange_service_id
            action_context['of_import_service_lines'] = True

        return action_context

    @api.multi
    def _affect_number(self):
        """ Affectation du numéro """
        for service in self:
            if service.base_state == 'calculated' and not service.number:
                number = self.env['ir.sequence'].next_by_code('of.service')
                service.write({'number': number})

    @api.model
    def of_get_report_name(self, docs):
        return "Demande d'intervention"

    @api.model
    def of_get_report_number(self, docs):
        if len(docs) == 1:
            return docs.number
        return ""

    @api.model
    def of_get_report_date(self, docs):
        if len(docs) == 1:
            lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
            return "%s " % format_date(docs.date_next, lang)
        return ""


class OfServiceLine(models.Model):
    _name = 'of.service.line'

    service_id = fields.Many2one(
        comodel_name='of.service', string=u"Demande d'intervention", required=True, ondelete='cascade')
    saleorder_line_id = fields.Many2one(
        comodel_name='sale.order.line', string=u"Ligne de vente",
        help=u"Utilisé pour savoir si une commande a été générée pour cette ligne.")
    so_number = fields.Char(
        string=u"Numéro de commande client", related='saleorder_line_id.order_id.name', readonly=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', related='service_id.partner_id', readonly=True)
    company_id = fields.Many2one(
        comodel_name='res.company', related='service_id.company_id', string=u'Société', readonly=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', string=u"Devise", readonly=True, related='company_id.currency_id')

    product_id = fields.Many2one(comodel_name='product.product', string=u"Article")
    price_unit = fields.Monetary(
        string=u"Prix unitaire", digits=dp.get_precision('Product Price'), default=0.0, currency_field='currency_id'
    )
    qty = fields.Float(string=u"Qté", digits=dp.get_precision('Product Unit of Measure'))
    name = fields.Text(string=u"Description")
    taxe_ids = fields.Many2many(comodel_name='account.tax', string=u"TVA")
    discount = fields.Float(string=u"Remise (%)", digits=dp.get_precision('Discount'), default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string=u"Sous-total HT", readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string=u"Taxes", readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string=u"Sous-total TTC", readonly=True, store=True)
    invoice_status = fields.Selection(selection=[
        ('no', u"Rien à facturer"),
        ('to invoice', u"À facturer"),
        ('invoiced', u"Totalement facturée"),
    ], string=u"État de facturation", compute='_compute_invoice_status', store=True)
    qty_invoiced = fields.Float(string=u"Qté facturée", compute='_compute_qty_invoiced', store=True)
    qty_invoiceable = fields.Float(string=u"Qté a facturer", compute='_compute_qty_invoiceable', store=True)
    invoice_line_ids = fields.One2many(
        'account.invoice.line', 'of_service_line_id', string=u"Ligne de facturation")

    @api.depends('qty', 'price_unit', 'taxe_ids')
    def _compute_amount(self):
        u"""
        Calcule le montant de la ligne.
        """
        for line in self:
            company = line.service_id.company_id
            # arrondir est le fonctionnement par défaut
            with_round = not company or company.tax_calculation_rounding_method != 'round_globally'
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxe_ids.with_context(round=with_round).compute_all(
                price, line.currency_id, line.qty, product=line.product_id, partner=line.service_id.address_id)
            if not with_round:
                # on fait une troncature ici, car le "update" arrondi automatiquement
                taxes['total_included'] = int(taxes['total_included'] * 100) / 100.0
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
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
            fiscal_position = line.service_id.fiscal_position_id
            taxes = product.taxes_id
            if partner.company_id:
                taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes, product, partner)
            line.taxe_ids = taxes

    @api.depends('invoice_line_ids', 'invoice_line_ids.invoice_id', 'invoice_line_ids.quantity',
                 'invoice_line_ids.invoice_id')
    def _compute_qty_invoiced(self):
        for line in self:
            line.qty_invoiced = sum(line.invoice_line_ids.mapped('quantity'))

    @api.depends('qty', 'qty_invoiced', 'saleorder_line_id')
    def _compute_qty_invoiceable(self):
        for line in self:
            if line.saleorder_line_id:
                line.qty_invoiceable = 0.0
            else:
                line.qty_invoiceable = line.qty - line.qty_invoiced

    @api.depends('qty', 'qty_invoiced', 'saleorder_line_id', 'qty_invoiceable')
    def _compute_invoice_status(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.saleorder_line_id:
                line.invoice_status = 'no'
            elif not float_is_zero(line.qty_invoiceable, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif float_compare(line.qty_invoiced, line.qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    @api.multi
    def prepare_intervention_line_vals(self):
        self.ensure_one()
        res = {
            'product_id': self.product_id and self.product_id.id or False,
            'price_unit': self.price_unit,
            'qty': self.qty,
            'name': self.name,
            'discount': self.discount,
            'order_line_id': self.saleorder_line_id and self.saleorder_line_id.id or False,
        }
        if self.taxe_ids:
            res['taxe_ids'] = [(6, 0, self.taxe_ids._ids)]
        return res

    @api.multi
    def prepare_so_line_vals(self, order):
        self.ensure_one()
        sale_line_obj = self.env['sale.order.line']
        # utilisation de new pour permettre les onchange
        order_line_new = sale_line_obj.new({
            'product_id': self.product_id.id,
            'order_id': order.id,
            'of_service_line_id': self.id,
        })
        order_line_new.product_id_change()
        order_line_new.product_uom_change()
        order_line_new.update({'product_uom_qty': self.qty})
        return order_line_new._convert_to_write(order_line_new._cache)

    @api.multi
    def _prepare_invoice_line(self):
        self.ensure_one()
        product = self.product_id
        partner = self.partner_id
        if not self.service_id.fiscal_position_id:
            return {}, u"Veuillez définir une position fiscale pour la demande d'intervention %s" % self.name
        fiscal_position = self.service_id.fiscal_position_id
        taxes = self.taxe_ids
        if taxes:
            company = self.service_id._get_invoicing_company(partner)
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
            'quantity': self.qty,
            'discount': 0.0,
            'uom_id': product.uom_id.id,
            'product_id': product.id,
            'invoice_line_tax_ids': [(6, 0, taxes._ids)],
            'of_service_line_id': self.id
        }, ""


class OfServiceType(models.Model):
    _name = 'of.service.type'

    name = fields.Char(string="Type de service")
    kanban_ids = fields.Many2many(comodel_name='of.service.stage', string=u"Étapes autorisées")


class OfServiceStage(models.Model):
    _name = 'of.service.stage'
    _order = 'sequence'

    name = fields.Char(string=u"Nom de l'étape")
    sequence = fields.Integer(string=u"Séquence")
    type_ids = fields.Many2many(comodel_name='of.service.type', string=u"Types autorisés")


class OFServiceTag(models.Model):
    _name = 'of.service.tag'
    _description = u"[obsolète] Étiquettes des services"

    name = fields.Char(string=u"Libellé", required=True)
    active = fields.Boolean(string='Actif', default=True)
    color = fields.Integer(string=u"Color index")


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    of_service_line_id = fields.Many2one(comodel_name='of.service.line', string=u"Ligne de DI")
