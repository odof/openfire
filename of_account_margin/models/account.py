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

    of_unit_cost = fields.Float(
        compute='_compute_of_unit_cost', inverse='_set_of_unit_cost', string=u"Coût unitaire",
        digits=dp.get_precision('Product Price'), store=True)
    of_margin = fields.Float(
        compute='_compute_of_margin', string=u"Marge", digits=dp.get_precision('Product Price'), store=True)

    @api.depends('product_id')
    def _compute_of_unit_cost(self):
        for line in self:
            cost = 0.0
            if len(line.sale_line_ids) == 1:
                if line.sale_line_ids.of_is_kit:
                    purchase_lines = line.sale_line_ids.kit_id.kit_line_ids.mapped('procurement_ids').\
                        mapped('move_ids').mapped('move_orig_ids').mapped('purchase_line_id')
                else:
                    purchase_lines = line.sale_line_ids.procurement_ids.mapped('move_ids').mapped('move_orig_ids').\
                        mapped('purchase_line_id')
                cost = sum(purchase_lines.mapped('price_subtotal')) / sum(purchase_lines.mapped('product_qty')) \
                    if sum(purchase_lines.mapped('product_qty')) else 0.0
                cost *= line.product_id.property_of_purchase_coeff
            if cost == 0.0:
                if line.product_id.of_is_kit:
                    cost = line.product_id.cost_comps
                else:
                    cost = line.product_id.standard_price
            line.of_unit_cost = cost

    def _set_of_unit_cost(self):
        pass

    @api.depends('price_subtotal', 'of_unit_cost', 'quantity')
    def _compute_of_margin(self):
        for line in self:
            if line.invoice_id.type == 'out_invoice':
                line.of_margin = line.price_subtotal - (line.of_unit_cost * line.quantity)
            elif line.invoice_id.type == 'out_refund':
                line.of_margin = -(line.price_subtotal - (line.of_unit_cost * line.quantity))


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    of_margin = fields.Float(string=u"Marge", readonly=True)

    def _select(self):
        res = super(AccountInvoiceReport, self)._select()
        res += ", sub.of_margin"
        return res

    def _sub_select(self):
        res = super(AccountInvoiceReport, self)._sub_select()
        res += ", ail.of_margin"
        return res
