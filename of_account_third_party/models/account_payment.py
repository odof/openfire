# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("reconciled_invoice_ids", "payment_type", "partner_type", "partner_id")
    def _compute_destination_account_id(self):
        for payment in self:
            if payment.partner_id and not payment.reconciled_invoice_ids and not payment.is_internal_transfer:
                payment.partner_id.update_account(update_customer_account=True, update_supplier_account=True)
        return super()._compute_destination_account_id()
