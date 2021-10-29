# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class OfPlanningPlannification(models.AbstractModel):
    _name = 'of.planning.plannification'

    # @api.model_cr_context
    # def _auto_init(self):
    #     cr = self._cr
    #
    #
    #     res = super(OfPlanningPlannification, self)._auto_init()
    #     return res

    nbr_interv = fields.Integer(
        required=False, compute='_compute_nbr_interv', string="Nombre de visites",
        help=u"Nombre de RDV d'interventions dans l'année", store=True)
    interv_frequency_nbr = fields.Integer(string=u"Interval de fréquence (RDV)", required=True)
    interv_frequency = fields.Selection(selection=[
        ('month', 'Mois'),
        ('year', 'Ans'),
        ], string=u"Type de fréquence (RDV)", required=True)
    mois_reference_ids = fields.Many2many(comodel_name='of.mois', string=u"Mois de visite", required=True)
    intervention_template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template', string=u"Modèle d'intervention")
    tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche", required=True)

    @api.multi
    def _generate_services(self):
        """Fonction à implémenter pour générer les interventions à programmer"""
        raise NotImplementedError("A class inheriting from this one must implement '_generate_services' function")

    @api.depends('interv_frequency_nbr', 'interv_frequency', 'mois_reference_ids')
    def _compute_nbr_interv(self):
        for contract in self:
            if contract.interv_frequency == 'month':
                months = len(contract.mois_reference_ids)
                contract.nbr_interv = months * contract.interv_frequency_nbr
            elif contract.interv_frequency == 'year':
                contract.nbr_interv = contract.interv_frequency_nbr

    @api.onchange('intervention_template_id')
    def _onchange_intervention_template_id(self):
        if self.intervention_template_id:
            self.tache_id = self.intervention_template_id.tache_id


class OfService(models.Model):
    _name = 'of.service'
    _inherit = ['of.service', 'mail.thread']

    partner_code_magasin = fields.Char(string="Code magasin", related="partner_id.of_code_magasin", readonly=True)
    supplier_id = fields.Many2one(comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]")
    contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat")
    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="['|','|',('contract_id','=',contract_id),('partner_id','=',partner_id),('address_id','=',address_id)]"
    )
    contract_message = fields.Char(string="Infos SAV du contrat", compute="_compute_contract_message")
    transformed = fields.Boolean(string=u"Transfomé en contrat")

    # @api.depends

    @api.depends('contract_line_id', 'contract_line_id.use_sav', 'type_id')
    def _compute_contract_message(self):
        sav_type = self.env.ref('of_service_parc_installe.of_service_type_sav', raise_if_not_found=False)
        if sav_type:
            for service in self:
                if service.type_id.id == sav_type.id and service.contract_line_id.use_sav:
                    count = service.contract_line_id.remaining_sav
                    service.contract_message = "%s SAV restant(s) pour cette ligne de contrat" % count
                elif service.type_id.id == sav_type.id and service.contract_line_id:
                    service.contract_message = "Cette ligne de contrat n'utilise pas l'option SAV"

    # @api.onchange

    @api.onchange('address_id', 'tache_id')
    def _onchange_address_id(self):
        super(OfService, self)._onchange_address_id()
        if self.address_id:
            if self.address_id.of_prestataire_id:
                self.supplier_id = self.address_id.of_prestataire_id

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id and self.contract_id.partner_id:
            self.partner_id = self.contract_id.partner_id

    @api.onchange('contract_line_id')
    def onchange_contract_line_id(self):
        if self.contract_line_id and self.contract_line_id.address_id:
            self.address_id = self.contract_line_id.address_id
            self.parc_installe_id = self.contract_line_id.parc_installe_id

    @api.onchange('recurrence')
    def _onchange_recurrent(self):
        if self.recurrence:
            self.contract_id = False
            self.contract_line_id = False

    @api.onchange('contract_id', 'contract_line_id')
    def _onchange_contract_id(self):
        if self.contract_id or self.contract_line_id:
            self.recurrence = False

    # Actions

    @api.multi
    def get_action_view_intervention_context(self, action_context={}):
        context_vals = {}
        if self.contract_line_id:
            context_vals['default_contract_line_id'] = self.contract_line_id.id
        action_context.update(context_vals)
        return super(OfService, self).get_action_view_intervention_context(action_context)

    @api.multi
    def action_view_contract(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_contract').read()[0]
        action['domain'] = [('id', '=', self.contract_id.id)]
        return action

    # Autres

    @api.multi
    def transform_to_contract(self):
        payment_type = self.env.ref('of_contract_custom.of_contract_recurring_invoicing_payment_post-paid')
        contract_obj = self.env['of.contract']
        contract_line_obj = self.env['of.contract.line']
        for service in self:
            if not service.recurrence or service.transformed or not service.address_id:
                continue
            first_of_the_month = fields.Date.from_string(fields.Date.today()) + relativedelta(day=1)
            first_of_the_month = fields.Date.to_string(first_of_the_month)
            vals_contract = {
                'contract_type': 'simple',
                'reference': service.partner_id.ref or 'Contrat',
                'partner_id': service.partner_id.id,
                'recurring_rule_type': 'month',
                'recurring_invoicing_payment_id': payment_type.id,
                'renewal': True,
                'date_start': first_of_the_month > service.date_next and first_of_the_month or service.date_next,
                }
            vals_line = {
                'address_id': service.address_id.id,
                'frequency_type': 'month',
                'recurring_invoicing_payment_id': payment_type.id,
                'parc_installe_id': service.parc_installe_id.id,
                'tache_id': service.tache_id.id,
                'mois_reference_ids': [(4, mois.id) for mois in service.mois_ids],
                }
            if service.recurring_rule_type == 'monthly':
                nbr_interv = 12.0 / float(service.recurring_interval)
                if nbr_interv.is_integer() and (nbr_interv/float(len(service.mois_ids))).is_integer():
                    interv_per_month = nbr_interv/len(service.mois_ids)
                    vals_line['interv_frequency_nbr'] = interv_per_month
                    vals_line['interv_frequency'] = 'month'
                else:
                    vals_line['interv_frequency_nbr'] = int(nbr_interv)
                    vals_line['interv_frequency'] = 'year'
            else:
                vals_line['interv_frequency_nbr'] = 1
                vals_line['interv_frequency'] = 'year'
            print vals_contract
            new_contract = contract_obj.create(vals_contract)
            vals_line['contract_id'] = new_contract.id
            contract_line_obj.create(vals_line)
            service.transformed = True


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="service_id and [('service_ids','=',service_id)] or "
               "address_id and [('address_id','=',address_id)] or "
               "[]")
    contract_id = fields.Many2one(
            comodel_name='of.contract', string="Contrat",
            domain="service_id and [('service_ids','=',service_id)] or "
                   "partner_id and [('partner_id','=',partner_id)] or "
                   "address_id and [('partner_id','=',address_id)] or "
                   "[]")
    partner_code_magasin = fields.Char(string="Code magasin", related="partner_id.of_code_magasin", readonly=True)

    @api.onchange('contract_line_id')
    def _onchange_contract_line_id(self):
        if self.contract_line_id:
            self.contract_id = self.contract_line_id.contract_id
            self.address_id = self.contract_line_id.address_id or self.contract_line_id.partner_id

    @api.onchange('service_id')
    def _onchange_service_id(self):
        super(OfPlanningIntervention, self)._onchange_service_id()
        if self.service_id:
            self.contract_line_id = self.service_id.contract_line_id
            self.contract_id = self.service_id.contract_id
