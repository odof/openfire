# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_price_management_line_values(self):
        self.ensure_one()
        result = super()._prepare_price_management_line_values()
        result['state'] = (
            'included'
            if not self.of_product_forbidden_discount and bool(self.product_uom_qty and self.price_unit)
            else 'excluded'
        )
        return result
