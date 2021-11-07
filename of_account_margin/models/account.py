# -*- coding: utf-8 -*-

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_margin = fields.Float(compute='_compute_of_margin', string=u"Marge", digits=dp.get_precision('Product Price'))
    of_margin_perc = fields.Float(compute='_compute_of_margin', string=u"Marge %")

    @api.depends('invoice_line_ids')
    def _compute_of_margin(self):
        for invoice in self:
            if invoice.type in ('out_invoice', 'out_refund'):
                invoice.of_margin = sum(invoice.invoice_line_ids.mapped('of_margin'))
                cost = invoice.amount_untaxed - invoice.of_margin
                invoice.of_margin_perc = 100 * (1 - cost / invoice.amount_untaxed) if invoice.amount_untaxed else -100


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    of_purchase_price_unit = fields.Float(
        compute='_compute_of_purchase_price_unit', inverse='_set_of_purchase_price_unit',
        string=u"Prix d'achat unitaire", digits=dp.get_precision('Product Price'), store=True)
    of_margin = fields.Float(
        compute='_compute_of_margin', string=u"Marge", digits=dp.get_precision('Product Price'), store=True)

    @api.depends('product_id')
    def _compute_of_purchase_price_unit(self):
        for line in self:
            cost = 0.0
            if len(line.sale_line_ids) == 1:
                if line.sale_line_ids.of_is_kit:
                    purchase_lines = line.sale_line_ids.kit_id.kit_line_ids.mapped('procurement_ids').\
                        mapped('move_ids').mapped('move_orig_ids').mapped('purchase_line_id')
                else:
                    purchase_lines = line.sale_line_ids.procurement_ids.mapped('move_ids').mapped('move_orig_ids').\
                        mapped('purchase_line_id')
                cost = sum(purchase_lines.mapped('price_subtotal')) / line.quantity if line.quantity else 0.0
            if cost == 0.0:
                cost = line.product_id.standard_price
            line.of_purchase_price_unit = cost

    def _set_of_purchase_price_unit(self):
        pass

    @api.depends('price_subtotal', 'of_purchase_price_unit', 'quantity')
    def _compute_of_margin(self):
        for line in self:
            if line.invoice_id.type == 'out_invoice':
                line.of_margin = line.price_subtotal - (line.of_purchase_price_unit * line.quantity)
            elif line.invoice_id.type == 'out_refund':
                line.of_margin = -(line.price_subtotal - (line.of_purchase_price_unit * line.quantity))


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    of_margin = fields.Float(string=u"Marge", readonly=True)
    of_margin_perc = fields.Char(string=u"Marge %", compute='_compute_of_margin_perc')
    of_invoice_number = fields.Char(string=u"Numéro de facture", readonly=True)
    of_invoice_origin = fields.Char(string=u"Origine", readonly=True)

    def _select(self):
        res = super(AccountInvoiceReport, self)._select()
        res += """
            , sub.of_margin
            , sub.number    AS of_invoice_number
            , sub.origin    AS of_invoice_origin
        """
        return res

    def _sub_select(self):
        res = super(AccountInvoiceReport, self)._sub_select()
        res += """
            , ail.of_margin
            , ai.number
            , ai.origin
        """
        return res

    def _group_by(self):
        res = super(AccountInvoiceReport, self)._group_by()
        res += """
            , ai.number
            , ai.origin
        """
        return res

    @api.multi
    def _compute_of_margin_perc(self):
        for rec in self:
            if rec.price_total != 0:
                rec.of_margin_perc = \
                    '%.2f' % (100.0 * rec.of_margin / rec.price_total)
            else:
                rec.of_margin_perc = "N/E"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'of_margin' not in fields:
            fields.append('of_margin')
        if 'price_total' not in fields:
            fields.append('price_total')
        res = super(AccountInvoiceReport, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'of_margin_perc' in fields:
                if 'of_margin' in line and line['of_margin'] is not None and line.get('price_total', False):
                    line['of_margin_perc'] = \
                        ('%.2f' % (round(100.0 * line['of_margin'] / line['price_total'], 2))).replace('.', ',')
                else:
                    line['of_margin_perc'] = "N/E"
        return res
