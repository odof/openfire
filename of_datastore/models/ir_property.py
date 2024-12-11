# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from .of_datastore_model import DATASTORE_IND


class IrProperty(models.Model):
    _inherit = "ir.property"

    @api.model
    def _get_multi(self, name, model, ids):
        """Override to retrieve a company_dependent value from a centralized product"""
        result = {}

        model_obj = self.env[model]

        positive_ids = [i for i in ids if i > 0]
        negative_ids = [i for i in ids if i < 0]

        base_dict = {}
        for negative_id in negative_ids:
            base_id = -negative_id // DATASTORE_IND
            if base_id in base_dict:
                base_dict[base_id].append(negative_id)
            else:
                base_dict[base_id] = [negative_id]
        res = []
        datastore_supplier_obj = self.env["of.datastore.supplier"]
        for base_id in base_dict:
            base = datastore_supplier_obj.browse(base_id)
            res += model_obj.of_ds_read(base, base_dict[base_id], [name])

        for line in res:
            result = {line["id"]: line[name]}

        result |= super()._get_multi(name, model, positive_ids)
        return result
