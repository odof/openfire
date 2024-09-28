# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class RecoveryCylinder(models.Model):
    _name = "of.recovery.cylinder"
    _description = "Recovery Cylinder"

    active = fields.Boolean(default=True)
    name = fields.Char(string="Name", required=True)
    total_capacity = fields.Float(string="Total Capacity", required=True)
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=False)
    delivery_date = fields.Date(string="Delivery Date", required=False)
    fluid_type_id = fields.Many2one(comodel_name="of.fluid.type", string="Nature of the fluid R-", required=True)
    supplier_id = fields.Many2one(comodel_name="res.partner", string="Supplier")
    return_date = fields.Date("Return Date")

    def copy_data(self, default=None):
        new_defaults = {
            "name": _("%s (copy)") % (self.name),
        }
        default = dict(new_defaults, **(default or {}))
        return super().copy_data(default)
