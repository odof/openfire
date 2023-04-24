# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    of_custom_groupby = fields.Boolean(string="Force authorization for grouping")

    def _reflect_fields(self, model_names):
        super()._reflect_fields(model_names)
        query = "UPDATE ir_model_fields SET of_custom_groupby=%s WHERE model=%s AND name=%s"
        for model_name in model_names:
            for field_name, field in self.env[model_name]._fields.items():
                self._cr.execute(query, (getattr(field, 'of_custom_groupby', False), model_name, field.name))
