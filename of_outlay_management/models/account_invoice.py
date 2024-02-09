# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _prepare_invoice_line_from_po_line(self, line):
        res = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        res['of_analytic_section_id'] = line.of_analytic_section_id
        return res

    @api.model
    def invoice_line_move_line_get(self):
        # Transfert des sections analytiques aux écritures comptables
        invoice_line_obj = self.env['account.invoice.line']
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        for vals in res:
            vals['of_analytic_section_id'] = invoice_line_obj.browse(vals['invl_id']).of_analytic_section_id.id
        return res

    def inv_line_characteristic_hashcode(self, invoice_line):
        # Séparation des écritures comptables par section analytique
        result = super(AccountInvoice, self).inv_line_characteristic_hashcode(invoice_line)
        result += "-%s" % (invoice_line.get('of_analytic_section_id', 'False'))
        return result
