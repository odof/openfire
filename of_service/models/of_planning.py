# -*- encoding: utf-8 -*-

from odoo import api, models, fields


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    type_id = fields.Many2one(comodel_name='of.service.type', string="Type")
    segmentation_allowed = fields.Boolean(string=u"Segmentation autorisée")

    @api.multi
    def name_get(self):
        """Permet dans un RDV d'intervention de proposer les modèles d'un type différent entre parenthèses"""
        type_id = self._context.get('type_prio_id')
        ttype = type_id and self.env['of.service.type'].browse(type_id) or False
        result = []
        for template in self:
            meme_type = template.type_id and template.type_id.id == type_id if ttype else True
            result.append((template.id, "%s%s%s" % ('' if meme_type else '(',
                                                    template.name,
                                                    '' if meme_type else ')')))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un RDV d'intervention de proposer en priorité les modèles de même type"""
        if self._context.get('type_prio_id'):
            type_id = self._context.get('type_prio_id')
            args = args or []
            res = super(OfPlanningInterventionTemplate, self).name_search(
                name,
                args + [['type_id', '=', type_id], ['type_id', '!=', False]],
                operator,
                limit) or []
            # Attention : tester la nouvelle valeur limit. Limit = 0 revient au même que limit = None
            if not limit or len(res) < limit:
                res += super(OfPlanningInterventionTemplate, self).name_search(
                    name,
                    args + [['type_id', '=', False]],
                    operator,
                    limit and limit - len(res)) or []
            if not limit or len(res) < limit:
                res += super(OfPlanningInterventionTemplate, self).name_search(
                    name,
                    args + [['type_id', '!=', type_id], ['type_id', '!=', False]],
                    operator,
                    limit and limit - len(res)) or []
            return res
        return super(OfPlanningInterventionTemplate, self).name_search(name, args, operator, limit)


class OFPlanningTache(models.Model):
    _inherit = "of.planning.tache"

    service_ids = fields.One2many("of.service", "tache_id", string="Services")
    service_count = fields.Integer(compute='_compute_service_count')

    recurrence = fields.Boolean(u"Tâche récurrente?")
    recurring_rule_type = fields.Selection(
        [('monthly', 'Mois'),
         ('yearly', u'Année(s)')],
        string=u'Récurrence', default='yearly',
        help=u"Spécifier l'intervalle pour le calcul automatique de la date de prochaine planification dans les"
             u" interventions récurrentes.")
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1, help=u"Répéter (Mois/Années)")
    recurrence_display = fields.Char(string=u"Récurrence", compute="_compute_recurrence_display")  # pour la vue liste

    # @api.depends

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
                display = u"Tous les "
                # éviter d'afficher "tous les 1 ans"
                if tache.recurring_interval and tache.recurring_interval != 1:
                    display += str(tache.recurring_interval) + u" "
                if tache.recurring_rule_type == 'monthly':
                    display += u"mois"
                elif tache.recurring_rule_type == 'yearly':
                    display += u"ans"
            tache.recurrence_display = display

    # Héritages

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """permet d'afficher les tache recurrentes en premier en fonction du contexte"""
        rec_first = self._context.get('show_rec_icon_first', -1)
        if rec_first != -1:
            res = super(OFPlanningTache, self).name_search(
                name, args + [['recurrence', '=', rec_first]], operator, limit) or []
            limit = limit - len(res)
            res += super(OFPlanningTache, self).name_search(
                name, [['recurrence', '!=', rec_first]], operator, limit) or []
            return res
        return super(OFPlanningTache, self).name_search(name, args, operator, limit)


class OFPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    @api.model_cr_context
    def _auto_init(self):
        u"""
        Initialiser le champ type_id en fonction du type_id de la DI
        """
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.columns "
                   "WHERE table_name = 'of_planning_intervention' AND column_name = 'type_id'")
        exists = bool(cr.fetchall())
        res = super(OFPlanningIntervention, self)._auto_init()
        if not exists:
            cr.execute("UPDATE of_planning_intervention AS interv SET type_id = service.type_id "
                       "FROM of_service AS service WHERE interv.service_id = service.id")
            cr.commit()
        return res

    service_id = fields.Many2one(
        'of.service', string=u"Demande d'intervention",
        domain="address_id and ['|', ('address_id', '=', address_id), ('partner_id', '=', address_id)] or []")
    type_id = fields.Many2one(comodel_name='of.service.type', string="Type")

    # @api.onchange

    @api.onchange('template_id')
    def onchange_template_id(self):
        super(OFPlanningIntervention, self).onchange_template_id()
        if self.state == "draft" and self.template_id and not self._context.get('of_import_service_lines') \
                and self.template_id.type_id:
            self.type_id = self.template_id.type_id

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.tache_id = self.service_id.tache_id
            self.address_id = self.service_id.address_id or self.service_id.partner_id
            if self.service_id.order_id:
                self.order_id = self.service_id.order_id
            if self.service_id.type_id:
                # Quand le RDV a une DI associée, le type est en readonly dans le XML et donc n'est pas écrit
                # l'affectation de type n'est que cosmétique ici
                self.type_id = self.service_id.type_id
            if self._context.get('of_import_service_lines'):
                self.fiscal_position_id = self.service_id.fiscal_position_id
                line_vals = [(5,)]
                for line in self.service_id.line_ids:
                    line_vals.append((0, 0, line.prepare_intervention_line_vals()))
                self.line_ids = line_vals
            # self._origin contient les valeurs de l'enregistrement en BDD
            if hasattr(self, '_origin') and self._origin.service_id.note \
                    and self._origin.service_id.note in (self._origin.description_interne or u""):
                # Si la description de l'ancienne DI est encore présente, la retirer
                self.description_interne = self._origin.description_interne.replace(self._origin.service_id.note, u"")
            descriterne = self.description_interne or u""
            if self.service_id.note and self.service_id.note not in descriterne:
                # si la description de la nouvelle DI n'est pas déjà présente, la rajouter
                self.description_interne = descriterne + self.service_id.note

    # Héritages

    @api.multi
    def write(self, vals):
        state_interv = vals.get('state', False)
        # avoir une prise en compte de l'état 'during', on pourra créer une fonction "get_planif_states"
        # en cas d'ajout de nouveaux états pas planifiés
        # permet de gérer le cas 'confirm' -> 'during' -> 'cancel'
        planif_avant = state_interv in ('unfinished', 'cancel', 'postponed') and \
            self.filtered(lambda i: i.state not in ('unfinished', 'cancel', 'postponed')) or False
        # les cas 'cancel' -> 'during' -> 'confirm' ne peut pas arriver cf fonction find_interventions de of_mobile
        pas_planif_avant = state_interv in ('draft', 'confirm') and \
            self.filtered(lambda i: i.state in ('unfinished', 'cancel', 'postponed')) or False
        fait = state_interv == 'done'
        # vérif si modification de date -> champ date deadline qui prend en compte le forçage de date
        date_deadline_avant = {rdv.id: rdv.date_deadline for rdv in self}

        # Quand le RDV a une DI associée, le type est en readonly dans le XML et donc n'est pas écrit
        # On affecte donc le type en sous-marin
        if vals.get('service_id'):
            service = self.env['of.service'].browse(vals['service_id'])
            if service.type_id:
                vals['type_id'] = service.type_id.id

        res = super(OFPlanningIntervention, self).write(vals)

        if state_interv or any(date_deadline_avant[rdv.id] != rdv.date_deadline for rdv in self):
            for intervention in self:
                service = intervention.sudo().service_id
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
                elif fait and service.date_next_last <= intervention.date_date:
                    # mettre à jour l'ancienne date de prochaine planification
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

        # Quand le RDV a une DI associée, le type est en readonly dans le XML et donc n'est pas écrit
        # On affecte donc le type en sous-marin
        if vals.get('service_id'):
            service = self.env['of.service'].browse(vals['service_id'])
            if service.type_id:
                vals['type_id'] = service.type_id.id

        intervention = super(OFPlanningIntervention, self).create(vals)

        state_interv = vals.get('state', 'draft')
        service = intervention.service_id
        if service and service.recurrence:  # RDV Tech d'une intervention récurrente
            # ne pas calculer la date de prochaine planification si la durée restante du service n'est pas nulle
            if state_interv in ('draft', 'confirm', 'done') and not service.duree_restante:
                # calculer date de prochaine planification
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
            if intervention == service_last_rdv:
                # était la dernière intervention planifiée pour ce service -> rollback!
                date_next = service.get_date_proche(service.date_next_last or intervention.date_date)
                service.write({
                    'date_next': date_next,
                    'date_fin': service.get_fin_date(date_next),
                })

        return super(OFPlanningIntervention, self).unlink()
