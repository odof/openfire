# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_cost(self):
        if not self:
            return 0
        self.ensure_one()
        if self.cost_method == "standard" or self.categ_id.of_sale_cost == "standard":
            return self.standard_price
        else:
            return self.of_theoretical_cost
