# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_sample = fields.Boolean("Is sample", compute="_compute_is_sample", store=True)

    @api.depends('order_line', 'order_line.product_id', 'order_line.product_id.is_sample')
    def _compute_is_sample(self):
        self.is_sample = any(line.product_id.is_sample for line in self.order_line)
