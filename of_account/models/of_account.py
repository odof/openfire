# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

# Ajout de la fonction de fusion des factures
class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def _prepare_merge_data(self):
        invoice = self[0]
        res = {
            'name'              : [],
            'origin'            : [],
            'reference'         : [],
            'comment'           : [],
            'journal_id'        : invoice.journal_id.id,
            'partner_id'        : invoice.partner_id.id,
            'fiscal_position_id': invoice.fiscal_position_id.id,
            'date_invoice'      : invoice.date_invoice or False,
            'account_id'        : invoice.account_id.id,
            'reference_type'    : invoice.reference_type,
            'invoice_line_ids'  : [],
            'user_id'           : invoice.user_id and invoice.user_id.id or False,
            'partner_bank_id'   : invoice.partner_bank_id and invoice.partner_bank_id.id or False,
            'currency_id'       : invoice.currency_id.id,
            'payment_term_id'   : invoice.payment_term_id and invoice.payment_term_id.id or False,
            'state'             : 'draft',
            'type'              : invoice.type,
        }
        for invoice in self:
            # Champs a mettre en liste
            if invoice.name:
                res['name'].append(invoice.name)
            if invoice.origin:
                res['origin'].append(invoice.origin)
            if invoice.reference:
                res['reference'].append(invoice.reference)
            if invoice.comment:
                res['comment'].append(invoice.comment)

            if invoice.date_invoice:
                if not res['date_invoice'] or res['date_invoice'] > invoice.date_invoice:
                    res['date_invoice'] = invoice.date_invoice
            if invoice.user_id and not res['user_id']:
                res['user_id'] = invoice.user_id.id

            # Champs mis a False si differents d'une facture a l'autre
            unique_fields = ('partner_bank_id','payment_term_id')
            for field in unique_fields:
                if res[field]:
                    val = getattr(invoice, field)
                    if not val or val.id != res[field]:
                        res[field] = False

            for invoice_line in invoice.invoice_line_ids:
                line_data = {
                    'product_id'          : invoice_line.product_id and invoice_line.product_id.id or False,
                    'name'                : invoice_line.name or '',
                    'origin'              : invoice_line.origin or '',
                    'price_unit'          : invoice_line.price_unit,
                    'discount'            : invoice_line.discount or False,
                    'invoice_line_tax_ids': ((6, 0, tuple([tax.id for tax in invoice_line.invoice_line_tax_ids])),),
                    'account_id'          : invoice_line.account_id.id,
                    'account_analytic_id' : invoice_line.account_analytic_id.id,
                    'quantity'            : invoice_line.quantity,
                    'uom_id'              : invoice_line.uom_id.id,
                }
                res['invoice_line_ids'].append((0, 0, line_data))

        res['name'] = " ".join(res['name'])
        res['origin'] = " ".join(res['origin'])
        res['reference'] = " ".join(res['reference'])
        res['comment'] = "\n".join(res['comment'])
        return res

    @api.multi
    def do_merge(self):
        """
        To merge similar type of account invoices.
        Invoices will only be merged if:
        * Account Invoices are in draft
        * Account Invoices belong to the same partner
        * Account Invoices have same journal, adresse facture, compte, type reference, devise
        Lines will NOT be merged

         @return: {new_invoice_id: old_invoice_ids} for every new invoice
        """
        so_obj = self.env['sale.order']\
            if 'sale.order' in self.env.registry else False
        po_obj = self.env['purchase.order']\
            if 'purchase.order' in self.env.registry else False
        invoice_line_obj = self.env['account.invoice.line']
        anal_line_obj = self.env['account.analytic.line']
        cr = self._cr
        invoices = self.search([('id','in',self._ids),('state','=','draft'),('type','in',('in_invoice','out_invoice'))])
        # Clef de determination des factures a grouper
        key_fields = ('journal_id', 'partner_id', 'account_id', 'reference_type', 'currency_id', 'type')
        packed_invoices = {}
        for invoice in invoices:
            key = [getattr(invoice, field) for field in key_fields]
            packed_invoices.setdefault(tuple(key), []).append(invoice.id)

        res = {}
        for invoice_ids in packed_invoices.itervalues():
            if len(invoice_ids) < 2:
                continue
            invoices = self.browse(invoice_ids)
            invoice_data = invoices._prepare_merge_data()
            new_invoice = self.create(invoice_data)
            # compute invoice taxes
            new_invoice._onchange_invoice_line_ids()
            new_invoice_id = new_invoice.id
            res[new_invoice_id] = [invoice.id for invoice in invoices]

            # make triggers pointing to the old invoices point to the new invoice
            for invoice in invoices:
                inv_obj = self.env['account.invoice']
                inv_obj.redirect_workflow([(invoice.id, new_invoice_id)])
                self.signal_workflow('invoice_cancel')

            # make relation fields pointing to the old invoices point to the new invoice
            for rel_table in ('sale_order_invoice_rel','purchase_invoice_rel'):
                cr.execute("SELECT true FROM pg_tables WHERE tablename = '%s'" % (rel_table,))
                if cr.fetchall():
                    for invoice_id in res:
                        cr.execute('UPDATE %s SET invoice_id=%s WHERE invoice_id in %s' % (rel_table, invoice_id, tuple(res[invoice_id])))

            # Le code suivant est inspire du module OCA account_invoicing.account_invoice_merge

            # make link between original sale order or purchase order
            # None if sale is not installed
            # None if purchase is not installed
            for order_obj in (so_obj,po_obj):
                if order_obj:
                    todos = order_obj.search([('invoice_ids', 'in', invoice_ids)])
                    todos.write({'invoice_ids': [(4, invoice_id)]})
                    for order in todos:
                        for order_line in order.order_line:
                            invoice_line_ids = invoice_line_obj.search(
                                [('product_id', '=', order_line.product_id.id),
                                 ('invoice_id', '=', new_invoice_id)])
                            if invoice_line_ids:
                                order_line.write({'invoice_lines': [(6, 0, invoice_line_ids)]})
            # recreate link (if any) between original analytic account line
            # (invoice time sheet for example) and this new invoice
            if 'invoice_id' in anal_line_obj._columns:
                todos = anal_line_obj.search([('invoice_id', 'in', invoice_ids)])
                todos.write({'invoice_id': new_invoice_id})
        return res

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.one
    @api.depends('line_ids')
    def _get_default_line_name(self):
        self.default_line_name = self.line_ids and self.line_ids[-1].name or ""

    default_line_name = fields.Char(size=64, compute='_get_default_line_name')
