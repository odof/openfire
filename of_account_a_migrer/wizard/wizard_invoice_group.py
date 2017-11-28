# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class of_invoice_group(models.TransientModel):
    """
    Ce wizard va fusionner les factures brouillon
    """

    _name = "of.invoice.group"
    _description = "Fusionner les factures brouillon"

    @api.multi
    def merge_invoices(self):
        invoice_obj = self.env['account.invoice']
        action_obj = self.env['ir.actions.act_window']
        allinvoices = invoice_obj.browse(self._context.get('active_ids', [])).do_merge()
        invoice_ids = allinvoices.keys()
        inv_type = 'in_invoice'
        if invoice_ids:
            inv_type = invoice_obj.browse(invoice_ids[0]).type

        view_nb = inv_type == 'in_invoice' and '2' or '1'
        xml_id = 'action_invoice_tree' + view_nb

        result = action_obj.for_xml_id('account', xml_id)
        result['domain'] = "[('id','in', %s)]" % invoice_ids
        return result
