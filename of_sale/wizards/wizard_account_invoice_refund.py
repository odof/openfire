# -*- coding: utf-8 -*-

from odoo import models, api

class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        return super(AccountInvoiceRefund, self.with_context(of_mode=mode)).compute_refund(mode)
