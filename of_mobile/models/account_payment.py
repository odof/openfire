# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from odoo import api, fields, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one

logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    of_intervention_id = fields.Many2one(comodel_name='calendar.event', string="Intervention")
    of_intervention_invoice_id = fields.Many2one(comodel_name='account.move', string="Intervention Invoice")
    of_sale_id = fields.Many2one(comodel_name='sale.order', string="Sale Order")
    of_sale_invoice_id = fields.Many2one(comodel_name='account.move', string="Sale Invoice")
    of_type = fields.Selection(
        [('all', "All"), ('intervention', "Intervention"), ('sale', "Sale"), ('none', "None")],
        default='none',
        string="Type",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """When creating a payment, we will also create (and post) the invoice associated with the intervention
        or the sale order.

        Args:
            vals_list: The list of values to create the payments

        Returns:
            account.payment: The created payments
        """
        for vals in vals_list:
            if of_intervention_id := vals.get('of_intervention_id'):
                intervention = self.env['calendar.event'].browse(of_intervention_id)
                if intervention.of_template_id and intervention.of_template_id.mobile_payment:
                    invoice = intervention.action_mobile_create_invoice()
                    vals['of_intervention_invoice_id'] = invoice.id
                    if intervention.of_template_id and intervention.of_template_id.auto_confirm_invoice:
                        invoice.action_post()

            if of_sale_id := vals.get('of_sale_id'):
                sale = self.env['sale.order'].browse(of_sale_id)
                if sale.state == 'sale':
                    invoice = sale._create_invoices()
                    vals['of_sale_invoice_id'] = invoice.id
                    intervention = self.env['calendar.event'].search([('of_additional_sale_order_id', '=', of_sale_id)])
                    if intervention.of_template_id and intervention.of_template_id.auto_confirm_invoice:
                        invoice.action_post()

        return super().create(vals_list)

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if intervention := args.get('intervention'):
            mutation['of_intervention_id'] = many2one(self=self, model='calendar.event', input=intervention)

        if sale := args.get('sale'):
            mutation['of_sale_id'] = many2one(self=self, model='sale.order', input=sale)
        elif intervention_input := args.get('intervention'):
            intervention = self.env['calendar.event'].search([('id', '=', intervention_input.id)])
            if intervention.of_additional_sale_order_id:
                mutation['of_sale_id'] = intervention.of_additional_sale_order_id.id

        if ttype := args.get('ttype'):
            mutation['of_type'] = ttype._value_

        return mutation
