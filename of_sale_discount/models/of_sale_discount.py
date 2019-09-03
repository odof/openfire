# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp

from odoo.exceptions import UserError

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
                    for discount in map(float, line.of_discount_formula.replace(',', '.').split('+')):
                        price_percent *= (100 - discount) / 100.0
                except:
                    raise UserError("Formule de remise invalide :\n%s" % (line.of_discount_formula,))
            line.discount = 100.0 - price_percent

    discount = fields.Float(string='Discount (%)', compute='_get_discount', digits=dp.get_precision('Discount'), store=True)
    of_discount_formula = fields.Char("Remise (%)", help="Remise ou somme de remises.\nEg. \"40 + 10.5\" équivaut à \"46.3\"")

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id')
    def _onchange_discount(self):
        """
        Si la ligne de commande est associée à une règle de liste de prix de type "Pourcentage de remise"
          et qui doit affecter le champ remise (et non pas le prix unitaire),
          alors on empêche le calcul Odoo pour copier directement la formule de la règle dans le champ de remise de la ligne de commande.
        """
        if not (self.product_id and self.product_uom and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('sale.group_discount_per_so_line')):
            # Les éléments sont insuffisants, ou alors la liste de prix n'impacte pas le champ de remise de la ligne de commande (code Odoo).
            return

        # Recherche d'une règle de liste de prix applicable à la ligne de commande.
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)
        rule_id = (self.order_id.pricelist_id
                   .with_context(product_context)
                   .get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id))[1]
        rule = rule_id and self.env['product.pricelist.item'].browse(rule_id)

        if rule and rule.compute_price == 'percentage':
            self.of_discount_formula = rule.of_percent_price_formula
        else:
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
                    for discount in map(float, line.of_discount_formula.replace(',', '.').split('+')):
                        price_percent *= (100 - discount) / 100.0
                except:
                    raise UserError("Formule de remise invalide :\n%s" % (line.of_discount_formula,))
            line.discount = 100.0 - price_percent

    discount = fields.Float(string='Discount (%)', compute='_get_discount', digits=dp.get_precision('Discount'), store=True)
    of_discount_formula = fields.Char("Remise (%)", help="Remise ou somme de remises.\nEg. \"40 + 10.5\" équivaut à \"46.3\"")

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.model_cr_context
    def _auto_init(self):
        """
        Remplit le champ of_percent_price_formula en fontion de percent_price.
        """
        cr = self._cr
        super(PricelistItem, self)._auto_init()
        cr.execute("UPDATE product_pricelist_item "
                   "SET of_percent_price_formula = TEXT(percent_price)"
                   "WHERE of_percent_price_formula IS NULL AND percent_price != 0")

    percent_price = fields.Float('Percentage Price', compute='_compute_percent_price')
    of_percent_price_formula = fields.Char("Pourcentage (remise)", help="Remise ou somme de remises.\nEg. \"40 + 10.5\" équivaut à \"46.3\"")

    @api.depends('of_percent_price_formula')
    def _compute_percent_price(self):
        """
        Évalue la formule of_percent_price_formula pour remplir le champ percent_price
        """
        for line in self:
            price_percent = 100.0
            if line.of_percent_price_formula:
                try:
                    for discount in map(float, line.of_percent_price_formula.replace(',', '.').split('+')):
                        price_percent *= (100 - discount) / 100.0
                except:
                    raise UserError("Formule de remise invalide :\n%s" % (line.of_percent_price_formula,))
            line.percent_price = 100.0 - price_percent
