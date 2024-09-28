# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class OfFluidType(models.Model):
    _name = "of.fluid.type"
    _description = "Fluid Type"

    active = fields.Boolean("Active", default=True)
    name = fields.Char("Name", required=True)
    gwp = fields.Float("GWP", required=True, default=False)
    category = fields.Selection([("cfc", "CFC"), ("hcfc", "HCFC"), ("hfc", "HFC")], string="Category", required=True)

    def copy_data(self, default=None):
        new_defaults = {
            "name": _("%s (copy)") % (self.name),
        }
        default = dict(new_defaults, **(default or {}))
        return super().copy_data(default)
