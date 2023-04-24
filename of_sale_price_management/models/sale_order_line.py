# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_price_management_variation = fields.Float(string="Unit amount of price change related to price management")
    of_unit_price_variation = fields.Float(
        string="Unit amount of the price variation",
        compute='_compute_of_unit_price_variation',
        store=True,
        digits='Product Price',
        readonly=False,
    )

    @api.depends('price_reduce', 'of_price_management_variation', 'price_unit')
    def _compute_of_unit_price_variation(self):
        for line in self:
            line.of_unit_price_variation = line.of_price_management_variation + line.price_reduce - line.price_unit

    def _prepare_price_management_line_values(self):
        self.ensure_one()
        return {
            'order_line_id': self.id,
            'state': 'included',
            'sim_total_cost_tax_excl': self.purchase_price * self.product_uom_qty,
            'sim_total_price_tax_excl': self.price_subtotal,
            'sim_total_price_tax_incl': self.price_total,
        }
