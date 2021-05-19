# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def button_cancel(self):
        for move in self:
            journal = move.journal_id
            if journal.type in ('cash', 'bank') and not journal.of_cancel_moves \
                    and not self._context.get('of_cancel_payment_bank_deposit'):
                raise UserError(_(
                    'You cannot modify a posted entry of this journal.\n'
                    'First you should set the journal to allow cancelling entries.'))
        return super(AccountMove, self).button_cancel()
