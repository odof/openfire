# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_theoretical_cost = fields.Boolean(
        string=u"(OF) Coût unitaire",
        help=u"Si actif, prend le coût théorique de l'article (si défini) au lieu du prix de vente")

    @api.multi
    def set_of_theoretical_cost_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_theoretical_cost', self.of_theoretical_cost)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_margin(self, order_id, product_id, product_uom_id):
        """Override to use the theoretical cost instead of the standard cost price when the settings is set to True"""
        frm_cur = self.env.user.company_id.currency_id
        to_cur = order_id.pricelist_id.currency_id
        if self.env['ir.values'].get_default('sale.config.settings', 'of_theoretical_cost')\
                and product_id.of_theoretical_cost:
            purchase_price = product_id.of_theoretical_cost
        else:
            purchase_price = product_id.standard_price
        if product_uom_id != product_id.uom_id:
            purchase_price = product_id.uom_id._compute_price(purchase_price, product_uom_id)
        ctx = self.env.context.copy()
        ctx['date'] = order_id.date_order
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return price

    @api.model
    def _get_purchase_price(self, pricelist, product, product_uom, date):
        """Override to use the theoretical cost instead of the standard cost price when the settings is set to True"""
        frm_cur = self.env.user.company_id.currency_id
        to_cur = pricelist.currency_id
        if self.env['ir.values'].get_default('sale.config.settings', 'of_theoretical_cost')\
                and product.of_theoretical_cost:
            purchase_price = product.of_theoretical_cost
        else:
            purchase_price = product.standard_price
        if product_uom != product.uom_id:
            purchase_price = product.uom_id._compute_price(purchase_price, product_uom)
        ctx = self.env.context.copy()
        ctx['date'] = date
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return {'purchase_price': price}
