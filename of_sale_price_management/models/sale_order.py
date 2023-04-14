# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_view = fields.Boolean(  # TODO: move me to of_sale module when it will be migrated to v16
        string="Customer/Vendor view"
    )
    of_total_cost = fields.Monetary(  # TODO: move me to of_sale module when it will be migrated to v16
        compute='_compute_of_total_cost', string="Total cost price"
    )

    @api.depends('margin', 'amount_untaxed')
    def _compute_of_total_cost(self):
        for order in self:
            order.of_total_cost = order.amount_untaxed - order.margin

    def action_button_price_management(self):
        self.ensure_one()

        price_management_obj = self.env['of.sale.price.management.wizard']
        line_vals = [Command.create(line._prepare_price_management_line_values()) for line in self.order_line]
        price_management = price_management_obj.create(
            {
                'order_id': self.id,
                'line_ids': line_vals,
            }
        )

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': price_management_obj._name,
            'res_id': price_management.id,
            'target': 'current',
            'flags': {'initial_mode': 'edit', 'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
            'context': {'invoice_status': self.invoice_status},
        }
