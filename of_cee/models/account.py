# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_cee_number = fields.Char(string=u"Numéro CEE", help=u"Numéro de dossier CEE du client")
    of_is_cee = fields.Boolean(string=u"Est une facture CEE ?")

    @api.multi
    def unlink(self):
        orders = self.env['sale.order']
        for invoice in self.filtered(lambda inv: inv.of_is_cee):
            for line in invoice.invoice_line_ids:
                orders |= line.sale_line_ids.mapped('order_id')
        res = super(AccountInvoice, self).unlink()
        orders._compute_of_cee_invoice_status()
        return res
