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
    def calculate_duration(self):
        if self.of_is_kit and self.kit_id:
            kit_lines = self.kit_id.kit_line_ids
            total_duration = 0.0
            for kit_line in kit_lines:
                original_uom = kit_line.product_id.uom_id
                current_uom = kit_line.product_uom_id
                qty = kit_line.qty_per_kit
                product_duration = kit_line.product_id.of_duration_per_unit
                total_duration += (product_duration * current_uom._compute_quantity(qty, original_uom, round=False))
            self.of_duration = total_duration
        elif self.product_id:
            original_uom = self.product_id.uom_id
            current_uom = self.product_uom
            self.of_duration = self.product_id.of_duration_per_unit * \
                current_uom._compute_quantity(self.product_uom_qty, original_uom, round=False)

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        self.calculate_duration()
        return res

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        super(SaleOrderLine, self).product_uom_change()
        self.calculate_duration()

    @api.onchange('of_is_kit')
    def _onchange_of_is_kit(self):
        super(SaleOrderLine, self)._onchange_of_is_kit()
        self.calculate_duration()

    @api.onchange('kit_id')
    def _onchange_kit_id(self):
        super(SaleOrderLine, self)._onchange_of_is_kit()
        self.calculate_duration()

    @api.model
    def _new_line_for_template(self, data):
        new_line = super(SaleOrderLine, self)._new_line_for_template(data)
        new_line.calculate_duration()
        return new_line
