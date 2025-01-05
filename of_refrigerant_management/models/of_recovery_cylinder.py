# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


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
    fluid_transactions_ids = fields.One2many(comodel_name="of.fluid.transaction", inverse_name="recovery_cylinder_id", string="Fluid Transactions")
    filled_quantity = fields.Float(string="Filled Quantity", compute="_compute_filled_quantity")
    filled_percentage = fields.Float(string="Filled Percentage", compute="_compute_filled_percentage")


    @api.depends('fluid_transactions_ids')
    def _compute_filled_quantity(self):
        for record in self:
            record.filled_quantity = sum(transaction.quantity for transaction in record.fluid_transactions_ids)

    @api.depends('filled_quantity', 'total_capacity')
    def _compute_filled_percentage(self):
        for record in self:
            if record.total_capacity:
                record.filled_percentage = (record.filled_quantity / record.total_capacity) * 100
            else:
                record.filled_percentage = 0.0

    def copy_data(self, default=None):
        new_defaults = {
            "name": _("%s (copy)") % (self.name),
        }
        default = dict(new_defaults, **(default or {}))
        return super().copy_data(default)

    def action_new_transaction(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Fluid Transaction'),
            'res_model': 'of.fluid.transaction',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_recovery_cylinder_id': self.id,
            }
        }