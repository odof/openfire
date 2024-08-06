from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    of_payment_mode_id = fields.Many2one(
        comodel_name="of.payment.mode",
        string="Payment Mode",
        domain="[('payment_type', '=', payment_type)]",
    )
    of_ref_reglement = fields.Char(size=64, string="Payment reference")
    of_tag_ids = fields.Many2many(comodel_name="of.payment.tags", string="Payment tags")

    @api.onchange("of_payment_mode_id")
    def _onchange_of_payment_mode_id(self):
        if self.of_payment_mode_id:
            self.journal_id = self.of_payment_mode_id.journal_id
        else:
            self.journal_id = False

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals["of_payment_mode_id"] = self.of_payment_mode_id.id
        payment_vals["of_ref_reglement"] = self.of_ref_reglement
        payment_vals["of_tag_ids"] = self.of_tag_ids.ids
        return payment_vals
