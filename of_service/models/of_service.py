# -*- encoding: utf-8 -*-

from odoo import api, models, fields, _
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
        # Interdiction pour les interventions d'avoir une durée nulle: on passe la durée à 1 et l'état à 'annulé'
        # on pourra supprimer ce code une fois que toutes les bases seront passées en branche planning
        # en pensant bien à le répercuter sur of_migration ;) ;)
        cr.execute("UPDATE of_service SET duree = 1, base_state = 'cancel'"
                   "WHERE duree = 0")

        # Lors de la 1ère mise à jour après la refonte des planning (sept. 2019), on migre les données existantes.
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_service' AND column_name = 'recurrence'")
        existe_avant = bool(cr.fetchall())
        # /* modifications champs date_next, date_next_fin, date_fin, date_fin_contrat
        # à retirer dans quelques semaines
        cr.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'of_service' AND column_name = 'date_fin_contrat'")
        date_fin_contrat_avant = bool(cr.fetchall())
        ### */
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
            # On met le champ base_state à "calculated" quand state est différent de "cancel".
            cr.execute("UPDATE of_service SET base_state = 'calculated'")
            services = self.env['of.service'].search([])
            services = services.filtered(lambda s: s.date_last and (not s.date_next or fields.Date.from_string(s.date_last) >= fields.Date.from_string(s.date_next)))
            for service in services:
                service.date_next = service.get_next_date(service.date_last)
        # /* modifications champs date_next, date_next_fin, date_fin, date_fin_contrat
        # à retirer dans quelques semaines
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'of_service' AND column_name = 'date_fin_contrat'")
        date_fin_contrat_apres = bool(cr.fetchall())
        if not date_fin_contrat_avant and date_fin_contrat_apres: # mettre à jour les champs
            # On peuple le champ date_fin_contrat des services recurrents avec le champ date_fin
            cr.execute("UPDATE of_service "
                       "SET date_fin_contrat = date_fin "
                       "WHERE recurrence = 't'")
            # puis on recalcul date_fin pour les services recurrents
            cr.execute("UPDATE of_service "
                       "SET date_fin = (date_next + interval '1 month' - interval '1 day') "
                       "WHERE recurrence = 't'")
        ### */
        return res

    @api.constrains('date_next', 'date_fin')
    def check_alert_dates(self):
        for intervention in self:
            if intervention.alert_dates:
                raise UserError(_(u'Intervention (%s): Inchohérence dans les dates' % intervention.name))

    def _default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    @api.multi
    @api.depends('duree', 'intervention_ids', 'recurrence', 'intervention_ids.state', 'date_next')
    def _compute_durees(self):
        for service in self:
            # ne pas prendre les interventions annulées / reportées / non terminées
            plannings = service.intervention_ids.filtered(lambda p: p.state in ('draft', 'confirm', 'done'))
            if plannings:
                service.date_last = plannings.sorted('date', reverse=True)[0].date_date
            else:
                service.date_last = False

            if service.recurrence and service.date_next:
                # On cherche la durée planifiée pour l'occurence en cours. Il nous faut savoir quelle est l'occurrence en cours
                date_next_ref_str = service.get_date_proche(fields.Date.today())  # début d'occurence en cours
                date_fin_ref_str = service.get_fin_date(date_next_ref_str)  # fin d'occurence en cours
                date_next_ref_da = fields.Date.from_string(date_next_ref_str)
                date_fin_ref_da = fields.Date.from_string(date_fin_ref_str)
                # RDVs pris en avance. Récupération de date de fin de l'occurence précédente pour connaitre l'écart
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

            service.duree_planif = sum(plannings.mapped('duree'))
            service.duree_restante = service.duree > service.duree_planif and service.duree - service.duree_planif or 0

    @api.model
    def compute_state_poncrec_daily(self):
        services = self.search([('base_state', '=', False)])
        for service in services:
            service.base_state = 'calculated'
        services = self.search([('base_state', '=', 'calculated')])
        services._compute_state_poncrec()

    @api.multi
    @api.depends('date_next', 'date_fin_contrat', 'duree', 'base_state', 'recurrence', 'intervention_ids')
    def _compute_state_poncrec(self):
        for service in self:
            service_state = service.get_state_poncrec_date(fields.Date.context_today(self))
            if not service.recurrence:
                service.state_ponc = service_state
            service.state = service_state

    @api.multi
    def filter_state_poncrec_date(self, date_eval=fields.Date.today(), state_list=('to_plan', 'part_planned', 'late')):
        """Permet de calculer l'état d'un service à une date donnée"""
        services_pass = self.env['of.service']
        for service in self:
            service_state = service.get_state_poncrec_date(date_eval=date_eval, to_plan_avance=False)
            if service_state in state_list:
                services_pass |= service
        return services_pass

    @api.multi
    def get_state_poncrec_date(self, date_eval=fields.Date.today(), to_plan_avance=False):
        """Calcul l'état à une date donnée, est prévu pour être utilisé pour des dates futures"""
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
                # prochaine planification à faire moins d'un mois après
                # et pas de dernier RDV ou dernier RDV plus d'un mois avant: à planifier
                if il_y_a_un_mois_da <= date_next_da <= fin_to_plan_da and \
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
                # le service expire avant la date donnée ou avant la date de prochaine planif: terminé
                elif fin_contrat_da and (fin_contrat_da < date_next_da or fin_contrat_da < date_eval_da):
                    service_state = 'done'
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
    def get_color_map(self):
        u"""
        fonction pour la légende de la vue map
        """
        title = "Prochaine Planification"
        v0 = {'label': "Plus d'un mois", 'value': 'black'}
        v1 = {'label': u'Ce mois-ci', 'value': 'orange'}
        v2 = {'label': u'En retard', 'value': 'red'}
        return {"title": title, "values": (v0, v1, v2)}

    _sql_constraints = [
        ('duree_non_nulle_constraint',
         'CHECK ( duree != 0 )',
         _(u'La durée de l\'intervention ne peut pas être nulle!')),
    ]

    # template_id = fields.Many2one('of.mail.template', string='Contrat')
    partner_id = fields.Many2one('res.partner', string='Partenaire', required=True, ondelete='restrict')
    address_id = fields.Many2one('res.partner', string="Adresse d'intervention", ondelete='restrict')
    secteur_tech_id = fields.Many2one(related='address_id.of_secteur_tech_id', readonly=True,
                                      search="_search_secteur_tech_id")
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
    sav_id = fields.Many2one("project.issue", string="SAV",
                             domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois',
                                help=u"Mois préférés du client.")
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours',
                                default=_default_jours, help=u"Jours de disponibilité du client.")

    note = fields.Text('Notes')
    date_next = fields.Date(string="Prochaine planif", help=u"Date à partir de laquelle programmer le prochain RDV",
                            required=True)
    date_next_last = fields.Date('Prochaine planif (svg)', help=u"Champ pour conserver une possibilité de rollback")
    date_fin = fields.Date(string=u"Date de fin de planification",
                           help=u"Date à partir de laquelle l'intervention devient en retard de planifiaction")
    date_fin_contrat = fields.Date(u"Date de fin de contrat")

    # Partner-related fields
    address_address = fields.Char('Adresse', related='address_id.contact_address', readonly=True)
    address_zip = fields.Char('Code Postal', size=24, related='address_id.zip', oldname="partner_zip")
    address_city = fields.Char('Ville', related='address_id.city', oldname="partner_city")

    recurrence = fields.Boolean(string=u"Est récurrente", default=True)
    recurring_rule_type = fields.Selection([
        ('weekly', 'Semaine(s)'),
        ('monthly', 'Mois'),
        ('yearly', u'Année(s)'),
        ], string=u'Récurrence', default='yearly', help=u"Spécifier l'intervalle pour le calcul automatique de date de prochaine intervention dans les services.")
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1, help=u"Répéter (Mois/Années)")

    state_ponc = fields.Selection([
        ('draft', u'Brouillon'),  # état par défaut
        ('to_plan', u'À planifier'),  # pas d'intervention
        ('part_planned', u'Partiellement planifiée'),  # intervention(s) et durée restante supérieure à 0
        ('all_planned', u'Entièrement planifiée'),  # intervention(s) et durée restante == 0
        ('late', u'En retard de planification'),  # date de prochaine planification il y a plus d'un mois
        ('done', u'Fait'),  # intervention(s) et durée restante == 0 et date de fin dépassée
        ('cancel', u'Annulée'),  # manuellement décidé
    ], u'État', compute="_compute_state_poncrec", search="_search_state_ponc")

    state = fields.Selection([
        ('draft', u'Brouillon'),  # état par défaut
        ('to_plan', u'À planifier prochainement'),  # prochaine intervention dans moins d'un mois
        ('planned', u'Planifiée récemment'),  # dernière intervention il y a moins d'un mois
        ('planned_soon', u'Planifiée prochainement'),  # planifié pour dans moins d'un mois
        ('progress', u'En cours'),  # par défaut
        ('late', u'En retard de planification'),  # date de prochaine planification il y a plus d'un mois
        ('done', u'Terminée'),  # date de fin <= date du jour (rec) / durée restante == 0 et date de fin dépassée (ponc)
        ('part_planned', u'Partiellement planifiée'),  # intervention(s) et durée restante supérieure à 0
        ('all_planned', u'Entièrement planifiée'),  # intervention(s) et durée restante == 0
        ('cancel', u'Annulée'),  # manuellement décidé
        ], u'État de planification', compute="_compute_state_poncrec", store=True)

    base_state = fields.Selection([
        ('draft', u'Brouillon'),  # état par défaut
        ('calculated', u'Calculé'),  # équivalent a state=False mais utile en XML
        ('cancel', u'Annulé'),  # manuellement décidé
        ], u'État de calcul', default="draft", required=True)

    active = fields.Boolean(string="Active", default=True)

    intervention_ids = fields.One2many('of.planning.intervention', 'service_id', string="RDVs Tech", order="date DESC")
    intervention_count = fields.Integer(string='nombre de RDVs', compute='_compute_intervention_count')
    date_last = fields.Date(
        string=u'Dernier RDV', compute='_compute_durees', search='_search_last_date',
        help=u"Date du dernier RDV")

    # Champs de recherche
    date_fin_min = fields.Date(string=u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date(string=u"Date échéance max", compute='lambda *a, **k:{}')
    date_controle = fields.Date(string=u"Date de contrôle", compute='lambda *a, **k:{}')

    # Couleur de contrôle
    color = fields.Char(compute='_compute_color', string='Couleur', store=False)
    recurrence_tache = fields.Boolean(related='tache_id.recurrence', string=u"Récurrence tâche", readonly=True)

    # Alertes
    alert_dates = fields.Boolean(string=u"Incohérence dans les dates", compute="_compute_alert_dates")

    def _search_state_ponc(self, operator, operand):
        services = self.search([])
        res = safe_eval("services.filtered(lambda s: s.state_ponc %s %s)" % (operator, operand), {'services': services})
        return [('id', 'in', res.ids)]

    def _search_secteur_tech_id(self, operator, operand):
        services = self.search([])
        res = safe_eval("services.filtered(lambda s: s.secteur_tech_id %s %.2f)" % (operator, operand), {'services': services})
        return [('id', 'in', res.ids)]

    def _search_duree_restante(self, operator, operand):
        services = self.search([])
        res = safe_eval("services.filtered(lambda s: s.duree_restante %s %.2f)" % (operator, operand), {'services': services})
        return [('id', 'in', res.ids)]

    @api.depends('date_next', 'date_fin')
    def _compute_alert_dates(self):
        for intervention in self:
            intervention.alert_dates = intervention.date_next and intervention.date_fin \
                                       and intervention.date_next > intervention.date_fin

    @api.multi
    @api.depends('address_id', 'partner_id', 'tache_id')
    def _compute_name(self):
        for service in self:
            partner_name = service.partner_id.name or u''
            address_zip = service.address_id.zip or u''
            tache_name = service.tache_id.name or u''
            service.name = tache_name + " " + partner_name + " " + address_zip

    @api.depends('intervention_ids')
    @api.multi
    def _compute_intervention_count(self):
        for service in self:
            service.intervention_count = len(service.intervention_ids.filtered(
                lambda r: r.state in ('draft', 'confirm', 'done')))

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
        self.date_fin = self.get_fin_date()

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
        if self.date_next:
            self.date_fin = self.get_fin_date()

    @api.multi
    def get_date_proche(self, date_eval, return_string=True):
        """
        retrouve l'occurrence la plus proche de la date étudiée, dans le passé ou le futur
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
        if date_eval_mois_int in mois_ints:  # la date est déja sur un mois autorisé
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
        retrouve la date de prochaine planif de l'occurence suivante/précédente suivant le mode
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
                res_mois_int = min(mois_int_temp, key=lambda m: (abs(m - date_to_mois_int), m))
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
                res_mois_int = min(mois_int_temp, key=lambda m: (abs(m - date_to_mois_int), m))
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
        :param date_str: Date de prochaine planif à utuliser pour le calcul, sous format string
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
                elif self.sav_id:
                    # une semaine par défaut pour les SAV
                    date_fin += relativedelta(weeks=1)
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
            return relativedelta(months=interval, day=1)
        else:
            return relativedelta(years=interval, day=1)

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
        if self.intervention_ids:
            context['force_date_start'] = self.intervention_ids[-1].date_date
            context['search_default_service_id'] = self.id
        elif self.base_state != 'calculated' or self.state == 'done':
            # inhiber la création en vue calendrier si l'intervention n'est pas planifiable (brouillon, annulée, terminée)
            context['inhiber_create'] = True
            if self.state == 'done':
                param = u"terminée"
            else:
                param = self.base_state == 'cancel' and u"annulée" or u"qui n'est pas validée"
            context['inhiber_message'] = u"Vous ne pouvez pas créer de RDV pour une intervention %s." % param

        return context

    @api.multi
    def action_view_interventions(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]

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
                elif tache.recurring_rule_type == 'weekly':
                    display += u"semaines"
                elif tache.recurring_rule_type == 'monthly':
                    display += u"mois"
                elif tache.recurring_rule_type == 'yearly':
                    display += u"ans"
            tache.recurrence_display = display

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
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
        domain="address_id and ['|', ('address_id', '=', address_id), ('partner_id', '=', address_id)] or []") #,('tache_id','=','tache_id')

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
            self.address_id = self.service_id.address_id or self.service_id.partner_id

    @api.multi
    def write(self, vals):
        state_interv = vals.get('state', False)
        planif_avant = state_interv in ('unfinished', 'cancel', 'postponed') and self.filtered(lambda i: i.state in ('draft', 'confirm', 'done')) or False
        pas_planif_avant = state_interv in ('draft', 'confirm') and self.filtered(lambda i: i.state in ('unfinished', 'cancel', 'postponed')) or False
        fait = state_interv == 'done'
        # vérif si modification de date -> champ date deadline qui prend en compte le forçage de date
        date_deadline_avant = {rdv.id: rdv.date_deadline for rdv in self}
        res = super(OFPlanningIntervention, self).write(vals)
        date_deadline_change = {rdv.id: date_deadline_avant[rdv.id] != rdv.date_deadline for rdv in self}

        if state_interv or any(date_deadline_change):
            for intervention in self:
                service = intervention.service_id
                date_next = False
                if not service or not service.recurrence:
                    continue
                # l'intervention passe d'un état planifié à un état pas planifié
                if planif_avant and intervention in planif_avant:
                    # rétablir l'ancienne date de prochaine planification si elle existe
                    date_next = service.get_date_proche(service.date_next_last or intervention.date_date)
                # l'intervention passe d'un état pas planifié à un état planifié (mais pas fait)
                elif not fait and pas_planif_avant and intervention in pas_planif_avant:
                    # calculer et affecter la nouvelle date de prochaine planification
                    date_next = service.get_next_date(intervention.date_date)
                # l'intervention est marquée comme faite
                elif fait and service.date_next_last <= intervention.date_date:  # mettre à jour l'ancienne date de prochaine planification
                    service.date_next_last = service.date_next
                    date_next = service.get_next_date(intervention.date_date)
                # aucun des cas précédent mais la date de fin a changé: màj date_next
                elif date_deadline_avant[intervention.id] != intervention.date_deadline:
                    date_next = service.get_next_date(service.date_last)

                if date_next:
                    service.write({
                        'date_next': date_next,
                        'date_fin': service.get_fin_date(date_next),
                    })
        return res

    @api.model
    def create(self, vals):
        service_obj = self.env['of.service']
        service = vals.get('service_id') and service_obj.browse(vals['service_id'])
        if service:
            vals['order_id'] = service.order_id and service.order_id.id
        intervention = super(OFPlanningIntervention, self).create(vals)
        state_interv = vals.get('state', 'draft')
        service = intervention.service_id
        if service and service.recurrence:  # intervention d'un service récurrent
            # ne pas calculer la date de prochaine planification si la durée restante du service n'est pas nulle
            if state_interv in ('draft', 'confirm', 'done') and not service.duree_restante:  # calculer date de prochaine intervention
                if state_interv == 'done':  # mettre à jour l'ancienne date de prochaine intervention avant tout
                    service.date_next_last = service.date_next
                date_next = service.get_next_date(intervention.date_date)
                service.write({
                    'date_next': date_next,
                    'date_fin': service.get_fin_date(date_next),
                })

        return intervention

    @api.multi
    def unlink(self):
        for intervention in self:
            service = intervention.service_id
            if not service or not service.recurrence or not service.intervention_ids:
                continue
            service_last_rdv = service.intervention_ids.sorted('date', reverse=True)[0]
            if intervention == service_last_rdv:  # était la dernière intervention planifiée pour ce service -> rollback!
                date_next = service.get_date_proche(service.date_next_last or intervention.date_date)
                service.write({
                    'date_next': date_next,
                    'date_fin': service.get_fin_date(date_next),
                })

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
    a_programmer_ids = fields.Many2many('of.service', string=u"À programmer", compute="compute_a_programmer")
    a_programmer_count = fields.Integer(string='Nombre à programmer', compute='compute_a_programmer')
    recurrent_ids = fields.Many2many('of.service', string=u"Récurrents", compute="compute_a_programmer")
    recurrent_count = fields.Integer(string='Nombre recurrents', compute='compute_a_programmer')

    @api.multi
    def compute_a_programmer(self):
        service_obj = self.env['of.service']
        for partner in self:
            service_ids = service_obj.search([
                '|',
                    ('partner_id', 'child_of', partner.id),
                    ('address_id', 'child_of', partner.id),
            ])
            partner.a_programmer_ids = service_ids.filtered(lambda s: s.state in ('draft', 'to_plan', 'part_planned', 'late'))
            partner.a_programmer_count = len(partner.a_programmer_ids)
            partner.recurrent_ids = service_ids.filtered(lambda s: s.recurrence and s.state not in ('draft', 'done', 'cancel'))
            partner.recurrent_count = len(partner.recurrent_ids)

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

    @api.multi
    def _get_action_view_a_programmer_context(self, context={}):
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        context.update({
            'default_partner_id': self.id,
            'default_address_id': self.address_get(adr_pref=['delivery']) or self.id,
            'default_recurrence': False,
            'default_date_next': today_str,
            'default_date_fin': deux_semaines_str,
            'default_origin': u"[Partenaire] " + self.name,
            'bloquer_recurrence': True,
            'hide_bouton_planif': True,
            })
        return context

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]

        if len(self._ids) == 1:
            action['context'] = str(self._get_action_view_a_programmer_context())

        action['domain'] = [
            '|',
            ('partner_id', 'child_of', self.ids),
            ('address_id', 'child_of', self.ids),
            ('state', 'in', ('draft', 'to_plan', 'part_planned', 'late')),
        ]

        return action

    @api.multi
    def _get_action_view_recurrent_context(self, context={}):
        today_str = fields.Date.today()
        today_da = fields.Date.from_string(today_str)
        deux_semaines_da = today_da + timedelta(days=14)
        deux_semaines_str = fields.Date.to_string(deux_semaines_da)
        context.update({
            'default_partner_id': self.id,
            'default_address_id': self.address_get(adr_pref=['delivery']) or self.id,
            'default_recurrence': True,
            'default_date_next': today_str,
            'default_origin': u"[Partenaire] " + self.name,
            'hide_bouton_planif': True,
            'bloquer_recurrence': True,
            })
        return context

    @api.multi
    def action_view_recurrent(self):
        action = self.env.ref('of_service.action_of_service_rec_form_planning').read()[0]

        if len(self._ids) == 1:
            #context = 'context' in action and safe_eval(action['context']) or {}
            action['context'] = str(self._get_action_view_recurrent_context())

        action['domain'] = [
            '|',
                ('partner_id', 'child_of', self.ids),
                ('address_id', 'child_of', self.ids),
            ('recurrence', '=', True),
            ('state', 'not in', ('draft', 'done', 'cancel', 'late')),
        ]

        return action


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
