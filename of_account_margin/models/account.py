# -*- coding: utf-8 -*-

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_margin = fields.Float(compute='_compute_of_margin', string=u"Marge", digits=dp.get_precision('Product Price'))
    of_margin_perc = fields.Float(compute='_compute_of_margin', string=u"Marge %")
    of_margin_deposit_excl = fields.Float(
        compute='_compute_of_margin', string=u"Marge hors acompte (en €)", digits=dp.get_precision('Product Price'))
    of_margin_deposit_excl_perc = fields.Float(compute='_compute_of_margin', string=u"Marge hors acompte (en %)")

    @api.depends('invoice_line_ids')
    def _compute_of_margin(self):
        for invoice in self:
            if invoice.type in ('out_invoice', 'out_refund'):
                invoice.of_margin = sum(invoice.invoice_line_ids.mapped('of_margin'))
                cost = invoice.amount_untaxed - invoice.of_margin
                invoice.of_margin_perc = 100 * (1 - cost / invoice.amount_untaxed) if invoice.amount_untaxed else -100

                # Acompte exclus
                deposit_categ_id = self.env['ir.values'].get_default(
                    'sale.config.settings', 'of_deposit_product_categ_id_setting')
                lines_deposit_excl = invoice.invoice_line_ids.filtered(
                    lambda l: l.product_id.categ_id.id != deposit_categ_id)
                invoice.of_margin_deposit_excl = sum(lines_deposit_excl.mapped('of_margin'))
                amount_untaxed_deposit_excl = sum(lines_deposit_excl.mapped('price_subtotal'))
                cost_deposit_excl = amount_untaxed_deposit_excl - invoice.of_margin_deposit_excl
                invoice.of_margin_deposit_excl_perc = 100 * (1 - cost_deposit_excl / amount_untaxed_deposit_excl) \
                    if amount_untaxed_deposit_excl else -100


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr

        cr.execute("SELECT * FROM information_schema.columns WHERE table_name = '%s' "
                   "AND column_name = 'of_unit_cost'" % (self._table,))
        exists = cr.fetchall()
        # On crée la colonne manuellement pour éviter le calcul sur toutes les lignes existantes (trop long)
        if not exists:
            cr.execute("ALTER TABLE account_invoice_line ADD COLUMN of_unit_cost numeric;")

        cr.execute("SELECT * FROM information_schema.columns WHERE table_name = '%s' "
                   "AND column_name = 'of_purchase_price'" % (self._table,))
        exists = cr.fetchall()
        # On crée la colonne manuellement pour éviter le calcul sur toutes les lignes existantes (trop long)
        if not exists:
            cr.execute("ALTER TABLE account_invoice_line ADD COLUMN of_purchase_price numeric;")

        return super(AccountInvoiceLine, self)._auto_init()

    of_unit_cost = fields.Float(
        compute='_compute_of_cost', inverse='_set_of_cost', string=u"Coût",
        digits=dp.get_precision('Product Price'), store=True, oldname='of_purchase_price_unit')
    of_purchase_price = fields.Float(
        compute='_compute_of_cost', inverse='_set_of_cost', string=u"Prix d'achat",
        digits=dp.get_precision('Product Price'), store=True)
    of_margin = fields.Float(
        compute='_compute_of_margin', string=u"Marge", digits=dp.get_precision('Product Price'), store=True)

    @api.depends('product_id')
    def _compute_of_cost(self):
        for line in self:
            if len(line.sale_line_ids) == 1 and not line.sale_line_ids.of_is_kit:
                purchase_lines = line.sale_line_ids.mapped('procurement_ids.move_ids.move_orig_ids.purchase_line_id')
                purchase_lines |= line.sale_line_ids.mapped('procurement_ids.move_ids.purchase_line_id')
                purchase_price_subtotal = sum(purchase_lines.mapped('price_subtotal'))
                purchase_qty = sum(purchase_lines.mapped('product_qty'))
                purchase_unit_price = purchase_price_subtotal / purchase_qty if purchase_qty else 0.0
                purchase_cost = purchase_unit_price * line.product_id.property_of_purchase_coeff
                sale_qty = line.sale_line_ids.product_uom_qty
                if sale_qty and purchase_qty < sale_qty:
                    cost = ((purchase_cost * purchase_qty) +
                            (line.sale_line_ids.purchase_price * (sale_qty - purchase_qty))) / sale_qty
                    purchase_price = ((purchase_unit_price * purchase_qty) +
                                      (line.sale_line_ids.of_seller_price * (sale_qty - purchase_qty))) / sale_qty
                else:
                    cost = purchase_cost
                    purchase_price = purchase_unit_price
            elif len(line.sale_line_ids) == 1 and line.sale_line_ids.of_is_kit:
                cost = line.sale_line_ids.purchase_price
                purchase_price = line.sale_line_ids.of_seller_price
            else:
                if line.product_id.of_is_kit:
                    cost = line.product_id.cost_comps
                    purchase_price = line.product_id.seller_price_comps
                else:
                    cost = line.product_id.get_cost()
                    purchase_price = line.product_id.of_seller_price
            line.of_unit_cost = cost
            line.of_purchase_price = purchase_price

    def _set_of_cost(self):
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
