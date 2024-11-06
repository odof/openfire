# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    of_payment_mode_id = fields.Many2one(comodel_name="of.payment.mode", string="Payment Mode")

    def _compute_payment_method_line_id(self):
        super()._compute_payment_method_line_id()
        for record in self:
            if record.of_payment_mode_id:
                record.payment_method_line_id = record.of_payment_mode_id.payment_method_line_id.id
