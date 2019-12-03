# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import date
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import (rrule,
                            YEARLY,
                            MONTHLY,
                            WEEKLY,
                            DAILY)
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

import math

class OfService(models.Model):
    _name = "of.service"
    _inherit = "of.map.view.mixin"
    _description = "Service"

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        # Lors de la 1ère mise à jour après la refonte des planning (sept. 2019), on migre les données existantes.
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_service' AND column_name = 'recurrence'")
        existe_avant = bool(cr.fetchall())
        res = super(OfService, self)._auto_init()
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_service' AND column_name = 'recurrence'")
        existe_apres = bool(cr.fetchall())
        # Si le champ recurrence n'existe pas avant et l'est après la mise à jour,
        # c'est qu'on est à la 1ère mise à jour après la refonte du planning, on doit faire la migration des données.
        if not existe_avant and existe_apres:
            # On peuple le champ durée des services avec la durée de la tâche associée au service.
            cr.execute("UPDATE of_service "
                       "SET duree = of_planning_tache.duree "
                       "FROM of_planning_tache "
                       "WHERE of_service.tache_id = of_planning_tache.id")
            # On met le champ state à "calculated" quand state est différent de "cancel".
            cr.execute("UPDATE of_service SET base_state = 'calculated'")
            services = self.env['of.service'].search([])
            services = services.filtered(lambda s: s.date_last and (not s.date_next or fields.Date.from_string(s.date_last) >= fields.Date.from_string(s.date_next)))
            for service in services:
                service.date_next = service.get_next_date(service.date_last)
        return res

    def _default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    @api.multi
    @api.depends('tache_id', 'address_id', 'duree', 'intervention_ids', 'recurrence', 'recurring_interval', 'recurring_rule_type')
    def _compute_durees(self):
        for service in self:
            plannings = service.intervention_ids
            # ne pas prendre les interventions annulées / reportées / non terminées
            planning_filtered = plannings.filtered(lambda p: p.state in ('draft', 'confirm', 'done'))
            service.date_last = planning_filtered and planning_filtered[-1].date or False

            if service.recurrence:
                # les interventions faites il y a plus d'une periode ne sont pas a prendre en compte dans le calcul de la durée planifiée
                if service.recurring_rule_type == 'yearly':
                    days_rec = 365
                elif service.recurring_rule_type == 'monthly':
                    days_rec = 30
                else:
                    days_rec = 7
                days_rec *= service.recurring_interval
                periode_td = timedelta(days=days_rec)
                today_da = fields.Date.from_string(fields.Date.today())
                last_periode_str = fields.Date.to_string(today_da - periode_td)
                plannings = plannings.filtered(lambda p: p.date_date >= last_periode_str)

            service.duree_planif = sum(plannings.filtered(lambda p: p.state in ('draft', 'confirm', 'done')).mapped('duree'))
            service.duree_restante = service.duree > service.duree_planif and service.duree - service.duree_planif or 0

    @api.model
    def compute_state_poncrec_daily(self):
        services = self.search([('base_state', '=', False)])
        for service in services:
            service.base_state = 'calculated'
        services = self.search([('base_state', '=', 'calculated')])
        services._compute_state_poncrec()

    @api.multi
    @api.depends('date_next', 'duree', 'base_state', 'recurrence', 'intervention_ids')
    def _compute_state_poncrec(self):
        un_mois = timedelta(days=30)
        today_da = fields.Date.from_string(fields.Date.context_today(self))
        dans_un_mois_da = today_da + un_mois
        il_y_a_un_mois_da = today_da - un_mois
        for service in self:
            if service.base_state and service.base_state == 'calculated':
                date_next_da = fields.Date.from_string(service.date_next)
                date_last_da = service.date_last and fields.Date.from_string(service.date_last) or False
                date_fin_da = service.date_fin and fields.Date.from_string(service.date_fin) or date_next_da + relativedelta(days=14)
                if service.recurrence:
                    # service.state_ponc = False
                    if il_y_a_un_mois_da <= date_next_da <= today_da and \
                            (not date_last_da or date_last_da < il_y_a_un_mois_da):
                        # prochaine planification à faire dans moins d'un mois
                        # et pas de dernière intervention ou dernière intervention il y a plus d'un mois
                        service.state = 'to_plan'
                    elif date_last_da and (il_y_a_un_mois_da <= date_last_da <= today_da):  # dernière intervention il y a moins d'un mois
                        service.state = 'planned'
                    elif date_last_da and (today_da < date_last_da <= dans_un_mois_da):  # dernière intervention dans moins d'un mois
                        service.state = 'planned_soon'
                    elif date_next_da < il_y_a_un_mois_da:  # prochaine planification en retard de plus d'un mois
                        service.state = 'late'
                    elif date_fin_da and (date_fin_da < date_next_da or date_fin_da < today_da):  # le service a expiré ou expire avant la date de prochaine planif
                        service.state = 'done'
                    else:  # par défaut
                        service.state = 'progress'
                else:
                    # l'état 'annulé' est provoqué manuellement
                    # dans le cas d'un service ponctuel, le champ 'date_next' correspond à la date de début de la fourchette de planification
                    # et le champ 'date_fin' à la date de fin de la fourchette de planification
                    # service.state_rec = False
                    if date_fin_da < today_da and service.duree_restante != 0:  # la durée restante n'est pas nulle et la date de fin est dépassée
                        service.state = 'late'
                    elif not date_last_da:  # aucune intervention planifiée
                        service.state = 'to_plan'
                    elif service.duree_restante == 0 and date_last_da < today_da:  # durée restant == 0 et la dernière intervention planifiée est passée
                        service.state = 'done'
                    elif service.duree_restante == 0 and service.duree:  # durée restante == 0 et la dernière intervention planifiée est future
                        service.state = 'all_planned'
                    else:  # la durée restant n'est pas nulle et la date de fin est future
                        service.state = 'part_planned'
                    service.state_ponc = service.state
            else:
                service.state = service.base_state
                service.state_ponc = service.base_state

    @api.multi
    def filter_state_poncrec_date(self, date=fields.Date.today(), state_list=('to_plan', 'part_planned', 'late')):
        un_mois = relativedelta(months=1)
        date_filter_da = fields.Date.from_string(date)
        dans_un_mois_da = date_filter_da + un_mois
        il_y_a_un_mois_da = date_filter_da - un_mois
        services_pass = self.env['of.service']
        for service in self:
            if service.base_state and service.base_state == 'calculated':
                date_next_da = fields.Date.from_string(service.date_next)
                date_last_da = service.date_last and fields.Date.from_string(service.date_last) or False
                date_fin_da = service.date_fin and fields.Date.from_string(service.date_fin) or date_next_da + relativedelta(days=14)
                if service.recurrence:
                    # service.state_ponc = False
                    if il_y_a_un_mois_da <= date_next_da <= date_filter_da and \
                            (not date_last_da or date_last_da < il_y_a_un_mois_da):
                        # prochaine planification à faire dans moins d'un mois
                        # et pas de dernière intervention ou dernière intervention il y a plus d'un mois
                        service_state = 'to_plan'
                    elif date_last_da and (il_y_a_un_mois_da <= date_last_da <= date_filter_da):  # dernière intervention il y a moins d'un mois
                        service_state = 'planned'
                    elif date_last_da and (date_filter_da < date_last_da <= dans_un_mois_da):  # dernière intervention dans moins d'un mois
                        service_state = 'planned_soon'
                    elif date_next_da < il_y_a_un_mois_da:  # prochaine planification en retard de plus d'un mois
                        service_state = 'late'
                    elif date_fin_da and (date_fin_da < date_next_da or date_fin_da < date_filter_da):  # le service a expiré ou expire avant la date de prochaine planif
                        service_state = 'done'
                    else:  # par défaut
                        service_state = 'progress'
                else:
                    # l'état 'annulé' est provoqué manuellement
                    # dans le cas d'un service ponctuel, le champ 'date_next' correspond à la date de début de la fourchette de planification
                    # et le champ 'date_fin' à la date de fin de la fourchette de planification
                    # service.state_rec = False
                    if date_fin_da < date_filter_da and service.duree_restante != 0:  # la durée restante n'est pas nulle et la date de fin est dépassée
                        service_state = 'late'
                    elif not date_last_da:  # aucune intervention planifiée
                        service_state = 'to_plan'
                    elif service.duree_restante == 0 and date_last_da < date_filter_da:  # durée restant == 0 et la dernière intervention planifiée est passée
                        service_state = 'done'
                    elif service.duree_restante == 0 and service.duree:  # durée restante == 0 et la dernière intervention planifiée est future
                        service_state = 'all_planned'
                    else:  # la durée restant n'est pas nulle et la date de fin est future
                        service_state = 'part_planned'
            else:
                service_state = service.base_state
            if service_state in state_list:
                services_pass |= service
        return services_pass

    @api.model
    def _search_last_date(self, operator, operand):
        cr = self._cr

        query = ("SELECT s.id\n"
                 "FROM of_service AS s\n"
                 "LEFT JOIN of_planning_intervention AS p\n"
                 "  ON p.address_id = s.address_id\n"
                 "  AND p.tache_id = s.tache_id\n")

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

    @api.multi
    @api.depends('state')
    def _compute_color(self):
        u""" COULEURS :
        Gris  : service dont l'adresse n'a pas de coordonnées GPS, ou service inactif
        Orange: service dont la date de prochaine intervention est dans moins d'un mois
        Rouge : service dont la date de prochaine intervention est inférieure à la date courante (ou à self._context.get('date_next_max'))
        Noir  : autres services
        """
        #date_next_max = fields.Date.from_string(self._context.get('date_next_max') or fields.Date.today())

        for service in self:
            if service.state in ('planned', 'planned_soon', 'progress', 'done', 'all_planned'):
                service.color = 'black'
            elif service.state in ('to_plan', 'part_planned'):
                service.color = 'orange'
            elif service.state == 'late':
                service.color = 'red'
            else:
                service.color = 'gray'
            # date_next = fields.Date.from_string(service.date_next)
            # if not (service.address_id.geo_lat or service.address_id.geo_lng) or not service.active:
            #     service.color = 'gray'
            # elif date_next <= date_next_max:
            #     service.color = 'red'
            # elif date_next <= date_next_max + timedelta(days=30):
            #     service.color = 'orange'
            # else:
            #     service.color = 'black'

    @api.model
    def get_color_map(self):
        u"""
        fonction pour la légende de la vue map
        """
        title = "Prochaine Intervention"
        v0 = {'label': "Plus d'un mois", 'value': 'black'}
        v1 = {'label': u'Ce mois-ci', 'value': 'orange'}
        v2 = {'label': u'En retard', 'value': 'red'}
        return {"title": title, "values": (v0, v1, v2)}

    # template_id = fields.Many2one('of.mail.template', string='Contrat')
    partner_id = fields.Many2one('res.partner', string='Partenaire', required=True, ondelete='restrict')
    address_id = fields.Many2one('res.partner', string="Adresse d'intervention", ondelete='restrict')
    secteur_tech_id = fields.Many2one(related='address_id.of_secteur_tech_id', readonly=True)
    company_id = fields.Many2one('res.company', string=u"Société")

    # Champs ajoutés pour la vue map
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')
    precision = fields.Selection(related='address_id.precision')
    partner_name = fields.Char(related='partner_id.name')
    partner_mobile = fields.Char(related='partner_id.mobile')
    partner_phone = fields.Char(related='partner_id.phone')

    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=True)
    tache_categ_id = fields.Many2one(related="tache_id.tache_categ_id", readonly=True)
    name = fields.Char(u"Libellé", compute="_compute_name", store=True)
    tag_ids = fields.Many2many('of.service.tag', string=u"Étiquettes")
    tache_name = fields.Char(related="tache_id.name", readonly=True)
    duree = fields.Float(string=u"Durée estimée")
    duree_planif = fields.Float(string=u"Durée planifiée", compute="_compute_durees")
    duree_restante = fields.Float(string=u"Durée restante", compute="_compute_durees", search='_search_duree_restante')

    origin = fields.Char(string="Origine")
    order_id = fields.Many2one('sale.order', string="Commande client")

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois',
                                help=u"Mois préférés du client.")
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours',
                                default=_default_jours, help=u"Jours de disponibilité du client.")

    note = fields.Text('Notes')
    date_next = fields.Date(string="Prochaine planif", help=u"Date à partir de laquelle programmer la prochaine intervention", required=True)
    date_next_fin = fields.Date(
        string=u'Au plus tard le', compute="compute_date_next_fin", inverse="inverse_date_next_fin",
        help=u'Échéance de la prochaine planification')
    date_next_last = fields.Date('Prochaine planification', help=u"Champ pour conserver une possibilité de rollback")
    date_fin = fields.Date(u"Date d'échéance")

    # Partner-related fields
    address_address = fields.Char('Adresse', related='address_id.contact_address', readonly=True)
    address_zip = fields.Char('Code Postal', size=24, related='address_id.zip', oldname="partner_zip")
    address_city = fields.Char('Ville', related='address_id.city', oldname="partner_city")

    recurrence = fields.Boolean(string=u"Récurrence", default=True)
    recurring_rule_type = fields.Selection([
        #('daily', 'Jour(s)'),
        ('weekly', 'Semaine(s)'),
        ('monthly', 'Mois'),
        ('yearly', u'Année(s)'),
        ], string=u'Récurrence', default='yearly', help=u"Spécifier l'intervalle pour le calcul automatique de date de prochaine intervention dans les services.")
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1, help=u"Répéter (Mois/Années)")

    # state_rec = fields.Selection([
    #     ('draft', u'Brouillon'),  # état par défaut
    #     ('to_plan', u'À planifier prochainement'),  # prochaine planif à faire dans moins d'un mois
    #     ('planned_soon', u'Planifié prochainement'),  # planifié pour dans moins d'un mois
    #     ('planned', u'Planifié récemment'),  # dernière intervention il y a moins d'un mois
    #     ('progress', u'En cours'),  # par défaut
    #     ('late', u'En retard de planification'),  # date de prochaine planification il y a plus d'un mois
    #     ('done', u'Terminé'),  # date de fin <= date du jour
    #     ('cancel', u'Annulé'),  # manuellement décidé
    # ], u'État', compute="_compute_state_poncrec", store=True)
    #
    state_ponc = fields.Selection([
        ('draft', u'Brouillon'),  # état par défaut
        ('to_plan', u'À planifier'),  # pas d'intervention
        ('part_planned', u'Partiellement planifiée'),  # intervention(s) et durée restante supérieure à 0
        ('all_planned', u'Entièrement planifiée'),  # intervention(s) et durée restante == 0
        ('late', u'En retard de planification'),  # date de prochaine planification il y a plus d'un mois
        ('done', u'Fait'),  # intervention(s) et durée restante == 0 et date de fin dépassée
        ('cancel', u'Annulée'),  # manuellement décidé
    ], u'État', compute="_compute_state_poncrec")

    state = fields.Selection([
        ('draft', u'Brouillon'),  # état par défaut
        ('to_plan', u'À planifier prochainement'),  # prochaine intervention dans moins d'un mois
        ('planned', u'Planifiée récemment'),  # dernière intervention il y a moins d'un mois
        ('planned_soon', u'Planifiée prochainement'),  # planifié pour dans moins d'un mois
        ('progress', u'En cours'),  # par défaut
        ('late', u'En retard de planification'),  # date de prochaine planification il y a plus d'un mois
        ('done', u'Terminé / Annulé'),  # date de fin <= date du jour (rec) / durée restante == 0 et date de fin dépassée (ponc)
        ('part_planned', u'Partiellement planifiée'),  # intervention(s) et durée restante supérieure à 0
        ('all_planned', u'Entièrement planifiée'),  # intervention(s) et durée restante == 0
        ('cancel', u'Annulée'),  # manuellement décidé
        ('calculated', u'Calculé'),  # équivalent a state=False mais utile en XML
        ], u'État', help=u"Ce champ permet de choisir manuellement l'état du service", compute="_compute_state_poncrec", store=True)

    base_state = fields.Selection([
        ('draft', u'Brouillon'),  # état par défaut
        ('calculated', u'Calculé'),  # équivalent a state=False mais utile en XML
        ('cancel', u'Annulé'),  # manuellement décidé
        ], u'État', help=u"Ce champ permet de choisir manuellement l'état du service", default="draft", required=True)

    active = fields.Boolean(string="Active", default=True)

    #intervention_ids = fields.One2many('of.planning.intervention', 'service_id', string="Interventions", order="date DESC")
    intervention_ids = fields.One2many('of.planning.intervention', 'service_id', string="Interventions", order="date DESC")
    intervention_count = fields.Integer(string='Interventions', compute='_compute_intervention_count')
    date_last = fields.Date(
        string=u'Dernière intervention', compute='_compute_durees', search='_search_last_date',
        help=u"Date de la dernière intervention")

    # Champs de recherche
    date_fin_min = fields.Date(string=u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date(string=u"Date échéance max", compute='lambda *a, **k:{}')
    date_controle = fields.Date(string=u"Date de contrôle", compute='lambda *a, **k:{}')

    # Couleur de contrôle
    color = fields.Char(compute='_compute_color', string='Couleur', store=False)
    recurrence_tache = fields.Boolean(related='tache_id.recurrence', string=u"Récurrence tâche", readonly=True)

    def _search_duree_restante(self, operator, operand):
        services = self.search([])
        res = safe_eval("services.filtered(lambda s: s.duree_restante %s %.2f)" % (operator, operand), {'services': services})
        return [('id', 'in', res.ids)]

    @api.multi
    @api.depends('address_id', 'partner_id', 'tache_id')
    def _compute_name(self):
        for service in self:
            partner_name = service.partner_id.name or u''
            address_zip = service.address_id.zip or u''
            tache_name = service.tache_id.name or u''
            service.name = tache_name + " " + partner_name + " " + address_zip

    @api.multi
    @api.depends('date_next', 'date_fin', 'recurrence')
    def compute_date_next_fin(self):
        un_mois = relativedelta(months=1)
        for service in self:
            if not service.recurrence:
                service.date_next_fin = service.date_fin
            elif service.date_next:
                date_next_un_mois = fields.Date.from_string(service.date_next) + un_mois
                if not service.date_fin:
                    service.date_next_fin = fields.Date.to_string(date_next_un_mois)
                else:
                    date_fin_da = fields.Date.from_string(service.date_fin)
                    service.date_next_fin = fields.Date.to_string(min(date_next_un_mois, date_fin_da))

    def inverse_date_next_fin(self):
        for service in self:
            if not service.recurrence:
                service.date_fin = service.date_next_fin

    @api.depends('intervention_ids')
    @api.multi
    def _compute_intervention_count(self):
        for service in self:
            service.intervention_count = len(service.intervention_ids)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.ensure_one()
        if self.partner_id:
            self.address_id = self.partner_id
            self.company_id = self.partner_id.company_id

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        self.ensure_one()
        if self.tache_id and self.tache_id.recurrence == self.recurrence:
            if not self._context.get(u"bloquer_recurrence"):
                self.recurring_rule_type = self.tache_id.recurring_rule_type
                self.recurring_interval = self.tache_id.recurring_interval
        self.duree = self.tache_id.duree

    @api.onchange('date_next')
    def _onchange_date_next(self):
        # Remplissage automatique du mois en fonction de la date de prochaine intervention choisie
        # /!\ Un simple clic sur le champ date appelle cette fonction, et génère le mois avec la date courante
        #       avant que l'utilisateur ait confirmé son choix.
        #     Cette fonction doit donc être autorisée à écraser le mois déjà saisi
        #     Pour éviter les ennuis, elle est donc restreinte à un usage en mode création de nouveau service uniquement
        if self.date_next and not self._origin:  # <- signifie mode creation
            mois = self.env['of.mois'].search([('numero', '=', int(self.date_next[5:7]))])
            mois_id = mois[0] and mois[0].id or False
            if mois_id:
                self.mois_ids = [(4, mois_id, 0)]
        if self.date_next and not self.date_fin:
            date_fin = fields.Date.from_string(self.date_next)
            if self.recurrence:
                date_fin += self.get_relative_delta(self.recurring_rule_type, self.recurring_interval * 2)
            elif 'sav_id' in self._fields:
                date_fin += relativedelta(weeks=2)
            else:
                date_fin += relativedelta(months=1)
            self.date_fin = fields.Date.to_string(date_fin)
        elif self.date_next and self.date_fin and self.date_next > self.date_fin:
            raise UserError("La date de prochaine planification est postérieure à la date de fin.\n"
                            "Cela signifie que cette intervention ne sera plus jamais sélectionnée par les outils de planification.\n"
                            "Veuillez changer les dates si ce n'est pas ce que vous vouliez faire")

    @api.multi
    def get_next_date(self, date_str):
        """
        :param date_str: Date de dernière intervention à utuliser pour le calcul, sous format string
        :return: Date à partir de laquelle planifier la prochaine intervention
        :rtype string
        """
        self.ensure_one()
        if self.recurrence:
            mois_ints = self.mois_ids.mapped('numero') or range(1, 13)

            date_from_da = fields.Date.from_string(max(date_str, self.date_last))

            date_from_mois_int = date_from_da.month

            if date_from_mois_int not in mois_ints:
                # l'intervention n'a pas été planifiée le bon mois
                # on veut replacer la date sur un mois valide AVANT d'ajouter la periode, il nous faut savoir si l'intervention à été planifié en retard ou en avance
                mois_courant_int = date_from_mois_int

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
                if mois_passe_int > date_from_mois_int:
                    mois_passe_int -= 12
                if mois_futur_int < date_from_mois_int:
                    mois_futur_int += 12
                # Mois le plus proche de la date fournie
                mois_int = mois_passe_int if mois_passe_int + mois_futur_int > 2 * date_from_mois_int else mois_futur_int
                mois_int -= 1

                # A ce stade, mois_int est un numéro de mois de 0 à 11
                #   auquel a été ajouté/retiré 12 en fonction de l'année
                # Il ne reste donc plus qu'à calculer l'année et le mois réels
                annee_int = date_from_da.year + int(math.floor(mois_int / 12.0))
                mois_int = mois_int % 12 + 1
                date_from_da = date(annee_int, mois_int, 1)

            date_next_da = date_from_da + self.get_relative_delta(self.recurring_rule_type, self.recurring_interval)
            date_next_mois_int = date_next_da.month

            res_mois_int = min(mois_ints, key=lambda m: (m < date_next_mois_int, m))
            res_year_int = date_next_da.year + (res_mois_int < date_next_mois_int)

            return fields.Date.to_string(date(year=res_year_int, month=res_mois_int, day=1))
        else:
            return False

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        #elif recurring_rule_type == 'daily':
        #    return relativedelta(days=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval, day=1)
        else:
            return relativedelta(years=interval, day=1)

    @api.multi
    def toggle_recurrence(self):
        return self.write({'recurrence': not self.recurrence})

    @api.multi
    def get_action_view_interventions_context(self, context={}):
        context.update({
            'default_partner_id' : self.partner_id.id,
            'default_address_id' : self.address_id and self.address_id.id or self.partner_id.id,
            'default_tache_id'   : self.tache_id and self.tache_id.id or False,
            'default_duree'      : self.duree,
            'default_description': self.note,
            'default_service_id' : self.id,
            'create'             : self.base_state == 'calculated',
            'edit'               : self.base_state == 'calculated',
            'default_order_id'   : self.order_id and self.order_id.id or False,
            })
        return context

    @api.multi
    def action_view_interventions(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]

        action['domain'] = [('service_id', 'in', self.ids)]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            action['context'] = str(self.get_action_view_interventions_context(context))

        return action

    @api.model
    def create(self, vals):
        if vals.get('address_id') and not vals.get('partner_id'):
            address = self.env['res.partner'].browse(vals['address_id'])
            partner = address.parent_id or address
            vals['partner_id'] = partner.id
        return super(OfService, self).create(vals)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(OfService, self).search(args, offset, limit, order, count)
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(OfService, self).read(fields, load)
        return res

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


class OFServiceTag(models.Model):
    _name = 'of.service.tag'
    _description = u"Étiquettes des services"

    name = fields.Char(string=u"Libellé", required=True)
    active = fields.Boolean(string='Actif', default=True)
    color = fields.Integer(string=u"Color index")

class OFPlanningTache(models.Model):
    _inherit = "of.planning.tache"

    service_ids = fields.One2many("of.service", "tache_id", string="Services")
    service_count = fields.Integer(compute='_compute_service_count')

    recurrence = fields.Boolean(u"Tâche récurrente?")
    recurring_rule_type = fields.Selection([
        ('weekly', 'Semaine(s)'),
        ('monthly', 'Mois'),
        ('yearly', u'Année(s)'),
        ], string=u'Récurrence', default='monthly', help=u"Spécifier l'intervalle pour le calcul automatique de date de prochaine intervention dans les services.")
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1, help=u"Répéter (Jours/Semaines/Mois/Années)")
    recurrence_display = fields.Char(string=u"Récurrence", compute="_compute_recurrence_display")

    @api.multi
    @api.depends('service_ids')
    def _compute_service_count(self):
        for tache in self:
            tache.service_count = len(tache.service_ids)

    @api.multi
    @api.depends('recurrence', 'recurring_interval', 'recurring_rule_type')
    def _compute_recurrence_display(self):
        for tache in self:
            display = False
            if tache.recurrence:
                if tache.recurring_rule_type and tache.recurring_rule_type == 'weekly' :  # Féminin
                    display = u"Toutes les "
                else:
                    display = u"Tous les "
                if tache.recurring_interval and tache.recurring_interval != 1:
                    display += chr(tache.recurring_interval) + u" "
                #if tache.recurring_rule_type == 'daily':
                #    display += u"jours"
                elif tache.recurring_rule_type == 'weekly':
                    display += u"semaines"
                elif tache.recurring_rule_type == 'monthly':
                    display += u"mois"
                elif tache.recurring_rule_type == 'yearly':
                    display += u"ans"
            tache.recurrence_display = display

    @api.multi
    def get_next_date(self, date_str):  # Jamais appelée en python, est-ce le cas en JS ?
        self.ensure_one()
        if self.recurrence:
            date_from_da = fields.Date.from_string(date_str)
            date_next_da = date_from_da + self.get_relative_delta(self.recurring_rule_type, self.recurring_interval)

            return fields.Date.to_string(date_next_da)
        else:
            return False

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        #elif recurring_rule_type == 'daily':
        #    return relativedelta(days=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval)
        else:
            return relativedelta(years=interval)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """permet d'afficher les tache recurrentes en premier en fonction du contexte"""
        rec_first = self._context.get('show_rec_icon_first', -1)
        if rec_first != -1:
            res = super(OFPlanningTache, self).name_search(name, args + [['recurrence', '=', rec_first]], operator, limit) or []
            limit = limit - len(res)
            res += super(OFPlanningTache, self).name_search(name, [['recurrence', '!=', rec_first]], operator, limit) or []
            return res
        return super(OFPlanningTache, self).name_search(name, args, operator, limit)


class OFPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    service_id = fields.Many2one(
        'of.service', string=u"À programmer",
        domain="address_id and [('address_id', '=', address_id),('tache_id','=','tache_id')]")

    @api.onchange('address_id', 'tache_id')
    def _onchange_address_id(self):
        super(OFPlanningIntervention, self)._onchange_address_id()
        if self.address_id and self.address_id.service_address_ids and not self.service_id:
            if self.tache_id:
                service = self.address_id.service_address_ids.filtered(lambda x: x.tache_id.id == self.tache_id.id)
                self.service_id = service and service[0] or False
            else:
                self.service_id = self.address_id.service_address_ids[0]

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.tache_id = self.service_id.tache_id

    @api.multi
    def write(self, vals):
        #services = self.mapped('service_id').filtered(lambda s: s.recurrence)  # seulement les services récurrents sont affectés
        state_interv = vals.get('state', False)
        planif_avant = state_interv in ('unfinished', 'cancel', 'postponed') and self.filtered(lambda i: i.state in ('draft', 'confirm', 'done')) or False
        pas_planif_avant = state_interv in ('draft', 'confirm') and self.filtered(lambda i: i.state in ('unfinished', 'cancel', 'postponed')) or False
        fait = state_interv == 'done'
        res = super(OFPlanningIntervention, self).write(vals)

        if state_interv:
            for intervention in self:
                service = intervention.service_id
                if not service or not service.recurrence:
                    continue
                # l'intervention passe d'un état planifié à un état pas planifié
                if planif_avant and intervention in planif_avant:
                    # rétablir l'ancienne date de prochaine planification si elle existe
                    service.date_next = service.date_next_last or intervention.date_date
                # l'intervention passe d'un état pas planifié à un état planifié (mais pas fait)
                elif not fait and pas_planif_avant and intervention in pas_planif_avant:
                    # calculer et affecter la nouvelle date de prochaine planification
                    service.date_next = service.get_next_date(intervention.date_date)
                # l'intervention est marquée comme faite
                elif fait and service.date_next_last <= intervention.date_date:  # mettre à jour l'ancienne date de prochaine planification
                    service.date_next_last = service.date_next
                    service.date_next = service.get_next_date(intervention.date_date)
        return res

    @api.model
    def create(self, vals):
        service_obj = self.env['of.service']
        service = vals.get('service_id') and service_obj.browse(vals['service_id'])
        if service:
            vals['order_id'] = service.order_id and service.order_id.id
        intervention = super(OFPlanningIntervention, self).create(vals)
        state_interv = vals.get('state', False)
        if state_interv:
            service = intervention.service_id
            if service and service.recurrence:  # intervention d'un service récurrent
                # ne pas calculer la date de prochaine planification si la durée restante du service n'est pas nulle
                if state_interv in ('draft', 'confirm', 'done') and not service.duree_restante:  # calculer date de prochaine intervention
                    if state_interv == 'done':  # mettre à jour l'ancienne date de prochaine intervention avant tout
                        service.date_next_last = service.date_next
                    service.date_next = service.get_next_date(service.date_next)
            """elif service:  # intervention d'un service ponctuel
                if state_interv == 'done':
                    intervention.service_id.state = 'done'
                elif state_interv in ('draft', 'confirm'):"""

        return intervention

    @api.multi
    def unlink(self):
        for intervention in self:
            service = intervention.service_id
            if not service or not service.recurrence or not service.intervention_ids:
                continue
            if intervention == service.intervention_ids[0]:  # était la dernière intervention planifiée pour ce service -> rollback!
                service.date_next = service.date_next_last or intervention.date_date

        return super(OFPlanningIntervention, self).unlink()


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Utilisé pour ajouter bouton Interventions à Devis (see order_id many2one field above)
    of_a_programmer_ids = fields.One2many("of.service", "order_id", string=u"À programmer")

    of_a_programmer_count = fields.Integer(string=u"À programmer", compute='_compute_of_a_programmer_count')

    @api.depends('of_a_programmer_ids')
    @api.multi
    def _compute_of_a_programmer_count(self):
        for sale_order in self:
            sale_order.of_a_programmer_count = len(sale_order.of_a_programmer_ids)

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_service.of_sale_order_open_a_programmer').read()[0]

        action['domain'] = [('order_id', 'in', self.ids)]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_address_id': self.partner_shipping_id.id or self.partner_id.id,
                'default_order_id': self.id,
            })
            action['context'] = str(context)
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_address_id': self.partner_shipping_id and self.partner_shipping_id.id or self.partner_id.id,
            'default_recurrence': False,
            'default_date_next': today_str,
            'default_date_fin': deux_semaines_str,
            'default_origin': u"[Commande] " + self.name,
            'default_order_id': self.id,
            'bloquer_recurrence': True,
            'hide_bouton_planif': True,
        }
        return action


class ResPartner(models.Model):
    _inherit = "res.partner"

    service_address_ids = fields.One2many('of.service', 'address_id', string='Services', context={'active_test': False})
    service_partner_ids = fields.One2many(
        'of.service', 'partner_id', string='Services du partenaire', context={'active_test': False},
        help=u"Services liés au partenaire, incluant les services des contacts associés")

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.id,
            'default_address_id': self.address_get(adr_pref=['delivery']) or self.id,
            'default_recurrence': False,
            'default_date_next': today_str,
            'default_date_fin': deux_semaines_str,
            'default_origin': u"[Partenaire] " + self.name,
            'bloquer_recurrence': True,
            'hide_bouton_planif': True,
        }
        return action

#    @api.multi
#    def toggle_active(self):
#       """ Inverse the value of the field ``active`` on the records in ``self``. """
#        for service in self:
#            service.active = not service.active
#            if not service.active:
#                service.service_address_ids = False


class DateRangeGenerator(models.TransientModel):
    _inherit = 'date.range.generator'

    @api.model
    def auto_genere_quinzaines(self, date_start_str=False):
        dr_type_obj = self.env['date.range.type']
        type = dr_type_obj.search([('name', '=', 'Quinzaine civile')], limit=1)
        if not type:
            type = dr_type_obj.create({'name': 'Quinzaine civile', 'company_id': False, 'allow_overlap': False})
        if not date_start_str:
            dr = self.env['date.range'].search([('type_id', '=', type.id)], order="date_start DESC", limit=1)
            if not dr:
                year_int = fields.Date.from_string(fields.Date.today()).year
                date_start_str = fields.Date.to_string(date(year_int, 1, 1))
            else:
                # le lendemain de la dernière période en date
                date_start_da = fields.Date.from_string(dr.date_end) + timedelta(days=1)
                date_start_str = fields.Date.to_string(date_start_da)

        date_start_dt = fields.Datetime.from_string(date_start_str)
        year_int = date_start_dt.year
        year_str = str(year_int % 100)
        name_prefix = "Q-%s-" % year_str
        # replacer la date de début sur un lundi pour caler les quinzaine sur des semaines
        date_start_dt -= timedelta(days=date_start_dt.weekday())

        vals = {
            'name_prefix': name_prefix,
            'date_start': fields.Date.to_string(date_start_dt),
            'type_id': type.id,
            'company_id': False,
            'unit_of_time': WEEKLY,
            'duration_count': 2,
            'count': 27,
        }
        dr_gen = self.create(vals)
        date_ranges = dr_gen._compute_date_ranges()
        if date_ranges:
            # replacer la date de début de la première période sur le premier de l'an pour eviter les chevauchements de périodes
            dr_first_debut_da = date(year_int, 1, 1)
            date_ranges[0]['date_start'] = fields.Date.to_string(dr_first_debut_da)
            # replacer la date de fin de la dernière période sur le 31 décembre pour eviter les chevauchements de périodes
            dr_last_fin_da = date(year_int, 12, 31)
            date_ranges[-1]['date_end'] = fields.Date.to_string(dr_last_fin_da)
            for dr in date_ranges:
                self.env['date.range'].create(dr)
        return self.env['ir.actions.act_window'].for_xml_id(
            module='date_range', xml_id='date_range_action')
