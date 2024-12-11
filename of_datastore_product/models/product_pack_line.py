#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class ProductPackLine(models.Model):
    _name = "product.pack.line"
    _inherit = ["product.pack.line", "of.datastore.product.reference", "of.datastore.model"]

    def of_ds_fields_to_fetch(self):
        res = super().of_ds_fields_to_fetch()
        return list(set(res + ["product_id", "quantity", "parent_product_id"]))

    def of_ds_match_one2many(self, value, base_index, data):
        return [-(id_ + base_index) for id_ in value] if value else []
