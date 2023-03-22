# -*- coding: utf-8 -*-
from odoo import models, api


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    @api.model
    def _get_of_option_date(self):
        result = super(AccountPaymentTermLine, self)._get_of_option_date()
        for i in xrange(len(result)):
            if result[i][0] == 'invoice':
                i += 1
                break
        return result[:i] + [('order', 'Date de commande')] + result[i:]
