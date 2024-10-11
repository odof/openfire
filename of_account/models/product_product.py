# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def name_get(self):
        if not self.env.context.get("of_only_default_code"):
            return super().name_get()

        self.browse(self.ids).read(["default_code", "name"])  # prefetch only required fields
        return [
            (template.id, f"{template.default_code}") if template.default_code else (template.id, f"{template.name}")
            for template in self
        ]
