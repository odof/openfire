# -*- coding: utf-8 -*-

from odoo import models, api

class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        if mode == 'cancel':
            return super(AccountInvoiceRefund, self.with_context(of_mode='cancel')).compute_refund(mode)
        return super(AccountInvoiceRefund, self).compute_refund(mode)
