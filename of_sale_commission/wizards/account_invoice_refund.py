# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        commis = False
        if mode == 'modify':
            # Les commissions sont à répercuter sur la facture finale.
            commis = self.env['of.sale.commi'].sudo().search(
                [('invoice_id', 'in', self._context.get('active_ids', [])), ('state', '!=', 'cancel')])

        return super(
            AccountInvoiceRefund,
            self.with_context(of_commis_to_refund=commis)
        ).compute_refund(mode=mode)
