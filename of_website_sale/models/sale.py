# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        values = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty=qty)

        order_line = self.env['sale.order.line'].new(values)
        order_line.product_id_change()
        order_line_vals = order_line._convert_to_write(order_line._cache)

        if values.get('product_uom_qty') != order_line_vals.get('product_uom_qty'):
            order_line_vals['product_uom_qty'] = values['product_uom_qty']

        return order_line_vals

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, attributes=None, **kwargs):
        result = super(SaleOrder, self)._cart_update(
            product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, attributes=attributes, **kwargs)
        # FIX de l'utilisation de liste de prix avec discount_policy == 'without_discount'
        # (recalcul du champ discount de la ligne de commande).
        if result['quantity']:
            # Si la quantité vaut 0, la ligne vient d'être supprimée, il ne faut pas travailler dessus.
            self.env['sale.order.line'].browse(result['line_id']).sudo()._onchange_discount()
        return result
