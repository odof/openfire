# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_duration = fields.Float(string=u"Durée de pose prévisionnelle", compute="_compute_of_duration")

    @api.depends('order_line', 'order_line.of_duration')
    def _compute_of_duration(self):
        for order in self:
            order.of_duration = sum(order.order_line.mapped('of_duration'))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_duration = fields.Float(string=u"Durée de pose prévisionnelle")

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            original_uom = self.product_id.uom_id
            current_uom = self.product_uom
            self.of_duration = self.product_id.of_duration_per_unit * \
                current_uom._compute_quantity(self.product_uom_qty, original_uom, round=False)

        return res

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        super(SaleOrderLine, self).product_uom_change()
        if self.product_id:
            original_uom = self.product_id.uom_id
            current_uom = self.product_uom
            self.of_duration = self.product_id.of_duration_per_unit * \
                current_uom._compute_quantity(self.product_uom_qty, original_uom, round=False)
