# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('reconciled_invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if len(self) == 1 and not self.reconciled_invoice_ids and self.payment_type != 'transfer' and self.partner_id:
            self.partner_id.update_account()
        return super()._compute_destination_account_id()
