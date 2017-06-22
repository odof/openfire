# -*- coding: utf-8 -*-

from odoo import api, fields, models

class OFStockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_done(self):
        # Update delivered quantities on sale order lines that are not kits
        result = super(OFStockMove, self).action_done()
        # Update delivered quantities on sale order line components
        sale_order_components = self.filtered(lambda move: move.product_id.expense_policy == 'no').mapped('procurement_id.sale_comp_id') # bug mal initialisé sale_comp_id?
        for comp in sale_order_components:
            comp.qty_delivered = comp._get_delivered_qty()
        lines = sale_order_components.mapped('order_line_id')
        # Update delivered quantities on sale order lines that are kits
        for line in lines:
            line.qty_delivered = line._get_delivered_qty_hack()

        return result