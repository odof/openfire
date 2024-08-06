# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    of_payment_mode_id = fields.Many2one(
        comodel_name="of.payment.mode", string="Payment Mode", domain="[('payment_type', '=', payment_type)]"
    )
    of_ref_reglement = fields.Char(size=64, string="Payment reference")
    of_tag_ids = fields.Many2many(comodel_name="of.payment.tags", string="Payment tags")

    @api.onchange("of_payment_mode_id")
    def _onchange_of_payment_mode_id(self):
        if self.of_payment_mode_id:
            self.journal_id = self.of_payment_mode_id.journal_id
        else:
            self.journal_id = False
