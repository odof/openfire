# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    filter_refund = fields.Selection(selection=
        [
            ('cancel', 'Cancel: create refund and reconcile'),
            ('refund', 'Create a draft refund'),
            ('modify', 'Modify: create refund, reconcile and create a new draft invoice'),
        ], default=lambda s: s._get_filter_refund_default())

    @api.model
    def _get_filter_refund_default(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            if len(inv.payment_move_line_ids) != 0 and inv.state != 'paid':
                return 'refund'
            else:
                return 'cancel'
        return 'refund'
