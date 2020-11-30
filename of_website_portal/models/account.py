# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def of_get_printable_data(self):
        return super(AccountInvoice, self.sudo()).of_get_printable_data()
