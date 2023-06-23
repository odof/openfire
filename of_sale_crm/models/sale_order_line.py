# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_amount_to_invoice = fields.Float(
        string="Reste à facturer en €", compute="_compute_of_amount_to_invoice", store=True
    )

    @api.depends('product_uom_qty', 'qty_invoiced', 'price_unit', 'discount')
    def _compute_of_amount_to_invoice(self):
        for line in self:
            line.of_amount_to_invoice = (
                (line.product_uom_qty - line.qty_invoiced) * line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            )
