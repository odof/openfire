# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_delivery_slip_value(self):
        """
        Calculate the total sale value of the picking.

        :return: float The total sale value.
        """
        amount = 0.0
        for picking in self:
            for line in picking.move_ids:
                if line.sale_line_id:
                    sale_line = line.sale_line_id
                    tax = sale_line.tax_id
                    price = sale_line.price_unit * (1 - (sale_line.discount or 0.0) / 100.0)
                    amounts = tax.compute_all(
                        price,
                        sale_line.order_id.currency_id,
                        line.product_uom_qty,
                        product=sale_line.product_id,
                        partner=sale_line.order_id.partner_shipping_id,
                    )
                    amount += amounts['total_included']

        return self.sale_id.currency_id.round(amount) if amount else amount
