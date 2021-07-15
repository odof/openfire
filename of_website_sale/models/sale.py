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

        return order_line_vals
