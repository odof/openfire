# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
        """Fonction à implémenter pour générer les demandes d'intervention"""
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


class OFService(models.Model):
    _name = 'of.service'
    _inherit = ['of.service', 'mail.thread']

    @api.model
    def get_intervention_states(self):
        return self.env['of.planning.intervention']._fields['state'].selection

    partner_code_magasin = fields.Char(string="Code magasin", related="partner_id.of_code_magasin", readonly=True)
    supplier_id = fields.Many2one(comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]")
    contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat")
    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="['|','|',('contract_id','=',contract_id),('partner_id','=',partner_id),('address_id','=',address_id)]"
    )
    contract_message = fields.Char(string="Infos SAV du contrat", compute="_compute_contract_message")
    transformed = fields.Boolean(string=u"Transfomé en contrat")
    last_intervention_state = fields.Selection(
        selection=lambda r: r.get_intervention_states(), string=u"État du dernier RDV",
        compute='_compute_last_intervention_state')
    contract_invoice_id = fields.Many2one(comodel_name='account.invoice', string=u"Facture du contrat associé")
    contract_date_invoice = fields.Date(
        related='contract_invoice_id.date_invoice', string=u"Date de facture du contrat associé", readonly=True)
    contract_line_frequency_type = fields.Selection(
        related='contract_line_id.frequency_type', string=u"Fréquence de facturation de la ligne de contrat associée",
        readonly=True)
    gb_contract_invoice_id = fields.Many2one(
        comodel_name='account.invoice', compute=lambda s: None, search='_search_gb_contract_invoice_id',
        string="Factures du contrat associé", of_custom_groupby=True)

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

    @api.depends('intervention_ids.state')
    def _compute_last_intervention_state(self):
        for record in self:
            rdvs = record.intervention_ids.filtered(lambda r: r.state not in ['cancel, postponed'])
            if rdvs:
                record.last_intervention_state = rdvs[-1].state
            elif record.intervention_ids:
                record.last_intervention_state = record.intervention_ids[-1].state

    @api.depends('contract_id', 'contract_id.invoice_ids')
    def _compute_invoice_ids(self):
        super(OFService, self)._compute_invoice_ids()
        for service in self:
            if service.contract_id:
                service.invoice_ids |= service.contract_id.invoice_ids
                service.invoice_count = len(service.invoice_ids)

    @api.model
    def _search_gb_contract_invoice_id(self, operator, operand):
        if operator == '=' and operand is False:
            return ['|', ('contract_id', '=', False), ('contract_id.invoice_ids', '=', False)]
        return [('contract_id.invoice_ids', operator, operand)]

    # @api.onchange

    @api.onchange('address_id', 'tache_id')
    def _onchange_address_id(self):
        super(OFService, self)._onchange_address_id()
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
        return super(OFService, self).get_action_view_intervention_context(action_context)

    @api.multi
    def action_view_contract(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_contract').read()[0]
        action['domain'] = [('id', '=', self.contract_id.id)]
        return action

    # Autres

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """ Ajout de la possibilité de regrouper par facture(s) de contrat lié
        """
        if gb != 'gb_contract_invoice_id':
            return super(OFService, self)._read_group_process_groupby(gb, query)
        else:
            field_name = 'gb_contract_invoice_id'
            alias, _ = query.add_join(
                (self._table, 'account_invoice', 'contract_id', 'of_contract_id', field_name),
                implicit=False, outer=True,
            )
            qualified_field = '"%s".id' % (alias,)

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': qualified_field
        }

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
            new_contract = contract_obj.create(vals_contract)
            vals_line['contract_id'] = new_contract.id
            contract_line_obj.create(vals_line)
            service.transformed = True

    @api.multi
    def orderable_lines(self):
        lines = super(OFService, self).orderable_lines()
        if self._context.get('keep_contract_lines'):
            return lines
        return lines.filtered(lambda l: not l.of_contract_line_id)

    @api.multi
    def _prepare_invoice_lines(self):
        self.ensure_one()
        if self.contract_line_id:
            lines_data = []
            error = ''
            for line in self.line_ids.filtered(
                    lambda l: not l.saleorder_line_id and not l.invoice_line_ids and not l.of_contract_line_id):
                line_data, line_error = line._prepare_invoice_line()
                lines_data.append((0, 0, line_data))
                error += line_error
        else:
            lines_data, error = super(OFService, self)._prepare_invoice_lines()
        return lines_data, error


class OFServiceLine(models.Model):
    _inherit = 'of.service.line'

    of_contract_line_id = fields.Many2one(comodel_name='of.contract.line', string="Ligne de contrat")
    of_contract_product_id = fields.Many2one(comodel_name='of.contract.product', string="Article de contrat")

    @api.multi
    def prepare_intervention_line_vals(self):
        vals = super(OFServiceLine, self).prepare_intervention_line_vals()
        vals['of_contract_line_id'] = self.of_contract_line_id and self.of_contract_line_id.id or False
        vals['of_contract_product_id'] = self.of_contract_product_id and self.of_contract_product_id.id or False
        return vals

    @api.multi
    def prepare_po_line_vals(self, order):
        po_line_vals = super(OFServiceLine, self).prepare_po_line_vals(order)
        def get_date_planned(service):
            date = service.intervention_ids and service.intervention_ids[0].date or False
            if not date:
                date = fields.Datetime.to_string(
                    fields.Datetime.from_string(service.date_next) + relativedelta(hour=12))
            return date
        if self.of_contract_line_id:
            service = self.service_id
            po_line_vals['date_planned'] = get_date_planned(service)
            po_line_vals['name'] = 'name' in po_line_vals and po_line_vals['name'] + "\n%s" % service.tache_id.name or \
                                   service.tache_id.name
        return po_line_vals

    @api.multi
    def _get_po_supplier(self, supplier_mode='product_supplier'):
        if supplier_mode == 'service_supplier':
            return self.service_id.supplier_id
        else:
            return super(OFServiceLine, self)._get_po_supplier(supplier_mode=supplier_mode)


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

    @api.multi
    def _prepare_invoice(self):
        vals, message = super(OfPlanningIntervention, self)._prepare_invoice()
        # message n'est rempli que si il y a une erreur
        if not message:
            contracts = self.line_ids.mapped('of_contract_line_id').mapped('contract_id')
            if len(contracts) == 1:
                vals['of_contract_id'] = contracts.id
        return vals, message

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
            # Toutes les lignes sont liées à un contrat
            if interv.line_ids and not interv.line_ids.filtered(lambda l: not l.of_contract_line_id):
                msgs.append(u"Les lignes facturables du rendez-vous %s étant liées à des lignes de contrat "
                            u"veuillez effectuer la facturation depuis le contrat." % interv.name)
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
    def _prepare_invoice_lines(self):
        self.ensure_one()
        if self.contract_line_id:
            lines_data = []
            error = ''
            for line in self.line_ids.filtered(
                    lambda l: l.invoice_status == 'to invoice' and not l.order_line_id and not l.of_contract_line_id):
                line_data, line_error = line._prepare_invoice_line()
                lines_data.append((0, 0, line_data))
                error += line_error
        else:
            lines_data, error = super(OfPlanningIntervention, self)._prepare_invoice_lines()
        return lines_data, error


class OFPlanningInterventionLine(models.Model):
    _inherit = 'of.planning.intervention.line'

    of_contract_line_id = fields.Many2one(comodel_name='of.contract.line', string="Ligne de contrat")
    of_contract_product_id = fields.Many2one(comodel_name='of.contract.product', string="Article de contrat")

    @api.multi
    def _prepare_invoice_line(self):
        vals, message = super(OFPlanningInterventionLine, self)._prepare_invoice_line()
        # message n'est rempli que si il y a une erreur
        if not message:
            vals['of_contract_line_id'] = self.of_contract_line_id and self.of_contract_line_id.id or False
            vals['of_contract_supposed_date'] = self.of_contract_line_id and self.of_contract_line_id.next_date or False
            vals['of_contract_product_id'] = self.of_contract_product_id and self.of_contract_product_id.id or False
        return vals, message
