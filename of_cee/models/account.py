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

    @api.multi
    def of_get_edf_cee_printable_data(self):
        result = self.of_get_printable_data()
        report_lines = []
        groups = self.env['account.invoice.line'].read_group(
            [('invoice_id', '=', self.id)], ['product_id', 'price_subtotal'], ['product_id'])
        for group in groups:
            report_lines.append({
                'name': group['product_id'][1],
                'qty': 1.0,
                'tax': self.invoice_line_ids.filtered(
                    lambda l: l.product_id.id == group['product_id'][0]).mapped('invoice_line_tax_ids')[0].description,
                'subtotal': group['price_subtotal'],
            })
        result['lines'] = report_lines
        return result
