# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    cart_quantity = fields.Float(compute='_compute_cart_info')

    def _compute_cart_info(self):
        super(SaleOrder, self)._compute_cart_info()
        for order in self:
            order.cart_quantity = sum(order.mapped('website_order_line.product_uom_qty'))
