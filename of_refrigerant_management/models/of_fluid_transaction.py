# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from datetime import datetime

class OfFluidTransation(models.Model):
    _name = "of.fluid.transaction"
    _description = "Fluid Transaction"

    active = fields.Boolean("Active", default=True)
    recovery_cylinder_id = fields.Many2one(comodel_name="of.recovery.cylinder", string="Recovery Cylinder", required=True)
    quantity = fields.Float(string="Quantity", required=True)
    transaction_date = fields.Datetime(string="Transaction Date", default=lambda self: fields.Datetime.now(), required_=True)
    action_type = fields.Selection([
        ('closure', 'Closure'),
        ('transfer', 'Transfer'),
        ('loss', 'Loss'),
        ('recycling', 'Recycling')
    ], string="Action Type", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        print(self.env.context)
        res["recovery_cylinder_id"] = self.env.context.get("default_recovery_cylinder_id")
        return res
