# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class Property(models.Model):
    _inherit = "ir.property"

    @api.model
    def _get_multi(self, name, model, ids):
        """Override to retrieve a company_dependent value from a centralized product"""
        result = {}
        model_obj = self.env[model]
        if ids and hasattr(model_obj, "_of_read_datastore"):
            if ds_ids := [i for i in ids if i < 0]:
                ids = [i for i in ids if i >= 0]
                result = {d["id"]: d[name] for d in model_obj.browse(ds_ids)._of_read_datastore([name])}
        result |= super()._get_multi(name, model, ids)
        return result
