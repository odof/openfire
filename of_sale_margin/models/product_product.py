# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_cost(self):
        """Get the cost price of the product. This method is used in the _compute_purchase_price method of
        sale.order.line to get the cost price of the product.
        This method is created to be inherited/overridden by other modules to change the way the cost price is computed.
        """
        if not self:
            return 0
        self.ensure_one()
        return self.standard_price
