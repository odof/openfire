# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class ProductCategory(models.Model):
    _name = "product.category"
    _inherit = ["product.category", "of.datastore.model"]

    def of_ds_match_many2one(self, value, base_index, data):
        return (-(value[0] + base_index), value[1])

    def of_ds_fields_to_fetch(self):
        return ["id", "name", "display_name", "parent_path"]
