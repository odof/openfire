# -*- coding: utf-8 -*-

from odoo import api, fields, models

import odoo.addons.decimal_precision as dp


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _default_uom(self):
        weight_uom_id = self.env.ref('product.product_uom_kgm', raise_if_not_found=False)
        if not weight_uom_id:
            uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
            weight_uom_id = self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)],
                                                           limit=1)
        return weight_uom_id

    weight_uom_id = fields.Many2one(default=lambda s: s._default_uom())

    @api.multi
    def action_confirm(self):
        """
            Pass the carrier to the picking from the purchase order
        """
        moves_to_check = []
        for move in self:
            if move.purchase_line_id and move.purchase_line_id.order_id.of_carrier_id:
                moves_to_check += [move]
        res = super(StockMove, self).action_confirm()
        for move in moves_to_check:
            pickings = move.mapped('picking_id').filtered(lambda record: not record.carrier_id)
            if pickings:
                pickings.write({
                    'carrier_id': move.purchase_line_id.order_id.of_carrier_id.id,
                    })
                # Get correct carrier price
                for picking in pickings:
                    picking.onchange_carrier()
        return res
