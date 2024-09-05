# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    of_payment_mode_id = fields.Many2one(
        comodel_name="of.payment.mode",
        string="Payment Mode",
        domain="[('payment_type', '=', payment_type)]",
    )
    of_payment_ref = fields.Char(size=64, string="Payment reference")
    of_tag_ids = fields.Many2many(comodel_name="of.payment.tags", string="Payment tags")

    def _compute_payment_method_line_id(self):
        super()._compute_payment_method_line_id()
        for record in self:
            if record.of_payment_mode_id:
                record.payment_method_line_id = record.of_payment_mode_id.payment_method_line_id.id

    @api.depends("of_payment_mode_id")
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for wizard in self:
            if wizard.of_payment_mode_id:
                wizard.journal_id = wizard.of_payment_mode_id.journal_id
            else:
                wizard.journal_id = False

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals["of_payment_mode_id"] = self.of_payment_mode_id.id
        payment_vals["payment_reference"] = self.of_payment_ref
        payment_vals["of_tag_ids"] = self.of_tag_ids.ids
        return payment_vals
