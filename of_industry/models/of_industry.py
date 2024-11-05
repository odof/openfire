# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFIndustry(models.Model):
    "Industry"

    _name = "of.industry"
    _description = __doc__
    _order = "name"

    name = fields.Char(translate=True, required=True)
    code = fields.Char(required=True, readonly=True)
    content = fields.Text(translate=True, readonly=True)
    custom_content = fields.Text(translate=True)
    show_in_sales = fields.Boolean(help="Add technical information in sale line description", default=True)
    is_custom = fields.Boolean()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("content") and not vals.get("custom_content"):
                vals["custom_content"] = vals.get("content")
        return super().create(vals_list)

    def _get_content(self):
        self.ensure_one()
        return self.custom_content if self.is_custom else self.content
