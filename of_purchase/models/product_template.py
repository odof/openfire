# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    of_purchase_count = fields.Integer(compute="compute_of_purchase_count", string="Purchases")

    def compute_of_purchase_count(self):
        for template in self:
            template.of_purchase_count = sum(
                p.of_purchase_count for p in template.with_context(active_test=False).product_variant_ids
            )
        return True
