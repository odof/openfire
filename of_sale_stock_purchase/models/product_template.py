# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def get_cost(self):
        self.ensure_one()
        if self.cost_method == "standard" or self.categ_id.of_sale_cost == "standard":
            return self.standard_price
        else:
            return self.of_theoretical_cost
