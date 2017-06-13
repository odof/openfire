# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp

from odoo.exceptions import UserError, RedirectWarning, ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        super(SaleOrderLine, self)._auto_init()
        cr.execute("UPDATE sale_order_line "
                   "SET of_discount_formula = TEXT(discount)"
                   "WHERE of_discount_formula IS NULL AND discount != 0")

    @api.depends('of_discount_formula')
    def _get_discount(self):
        for line in self:
            price_percent = 100.0
            if line.of_discount_formula:
                try:
                    for discount in map(float, line.of_discount_formula.replace(',','.').split('+')):
                        price_percent *= (100 - discount) / 100.0
                except:
                    raise UserError("Formule de remise invalide :\n%s" % (line.of_discount_formula,))
            line.discount = 100.0 - price_percent

    discount = fields.Float(string='Discount (%)', compute='_get_discount', digits=dp.get_precision('Discount'), store=True)
    of_discount_formula = fields.Char("Remise (%)", help="Remise ou somme de remises.\nEg. \"40 + 10.5\" équivaut à \"46.3\"")

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id')
    def _onchange_discount(self):
        super(SaleOrderLine, self)._onchange_discount()
        self.of_discount_formula = self.discount and str(self.discount) or False

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res['of_discount_formula'] = self.of_discount_formula
        return res

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        super(AccountInvoiceLine, self)._auto_init()
        cr.execute("UPDATE sale_order_line "
                   "SET of_discount_formula = TEXT(discount)"
                   "WHERE of_discount_formula IS NULL AND discount != 0")

    @api.depends('of_discount_formula')
    def _get_discount(self):
        for line in self:
            price_percent = 100.0
            if line.of_discount_formula:
                try:
                    for discount in map(float, line.of_discount_formula.replace(',','.').split('+')):
                        price_percent *= (100 - discount) / 100.0
                except:
                    raise UserError("Formule de remise invalide :\n%s" % (line.of_discount_formula,))
            line.discount = 100.0 - price_percent

    discount = fields.Float(string='Discount (%)', compute='_get_discount', digits=dp.get_precision('Discount'), store=True)
    of_discount_formula = fields.Char("Remise (%)", help="Remise ou somme de remises.\nEg. \"40 + 10.5\" équivaut à \"46.3\"")
