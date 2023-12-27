# -*- coding: utf-8 -*-

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _refund_cleanup_lines(self, lines):
        result = super(AccountInvoice, self)._refund_cleanup_lines(lines)
        if lines._name == 'account.invoice.line' and self.env.context.get('of_refund_mode') not in ('cancel', 'modify'):
            for row in result:
                del row[2]['of_intervention_line_id']
        return result
