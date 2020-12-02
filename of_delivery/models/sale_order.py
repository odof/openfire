# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_id = fields.Many2one(
        "delivery.carrier", string="Delivery Method", domain="[('of_use_sale','=',True)]")

    @api.depends('carrier_id', 'order_line', 'amount_total')
    def _compute_delivery_price(self):
        for order in self:
            if order.state not in ('draft', 'sent'):
                # We do not want to recompute the shipping price of an already validated/done SO
                continue
            elif order.carrier_id.delivery_type != 'grid' and not order.order_line:
                # Prevent SOAP call to external shipping provider when SO has no lines yet
                continue
            else:
                order.delivery_price = order.company_id.currency_id.with_context(date=order.date_order).compute(
                        order.carrier_id.with_context(order_id=order.id).price, order.pricelist_id.currency_id)
