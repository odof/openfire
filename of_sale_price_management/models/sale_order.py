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
    of_product_forbidden_discount = fields.Boolean(string="Discount not allowed for this product")

    @api.depends('margin', 'amount_untaxed')
    def _compute_of_total_cost(self):
        for order in self:
            order.of_total_cost = order.amount_untaxed - order.margin

    def action_button_price_management(self):
        self.ensure_one()

        price_management_obj = self.env['of.sale.price.management.wizard']
        line_vals = []
        for line in self.order_line:
            values = {
                'order_line_id': line.id,
                'state': 'included'
                if not line.of_product_forbidden_discount and bool(line.product_uom_qty and line.price_unit)
                else 'excluded',
                'sim_total_cost_tax_excl': line.purchase_price * line.product_uom_qty,
                'sim_total_price_tax_excl': line.price_subtotal,
                'sim_total_price_tax_incl': line.price_total,
            }
            line_vals.append(Command.create(values))

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
