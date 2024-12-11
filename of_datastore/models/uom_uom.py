# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UomUom(models.Model):
    _name = "uom.uom"
    _inherit = ["uom.uom", "of.datastore.model"]

    of_datastore_res_ids = fields.Char(string="Datastore res_ids")

    def of_ds_match_many2one(self, value, base_index, data):
        return (-(value[0] + base_index), value[1])

    def of_ds_fields_to_fetch(self):
        res = super().of_ds_fields_to_fetch()
        return list(set(res + ["name", "uom_type", "factor", "category_id", "rounding"]))
