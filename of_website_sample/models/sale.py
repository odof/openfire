# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_is_sample = fields.Boolean("Is sample", compute="_compute_of_is_sample", store=True)

    @api.depends('order_line', 'order_line.product_id', 'order_line.product_id.of_is_sample')
    def _compute_of_is_sample(self):
        for order in self:
            order.of_is_sample = any(line.product_id.of_is_sample for line in order.order_line)
