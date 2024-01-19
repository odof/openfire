# -*- coding: utf-8 -*-

from odoo import api, models


class OFCostRecomputeWizard(models.TransientModel):
    _inherit = 'of.cost.recompute.wizard'

    @api.multi
    def _handle_order_lines(self, order_lines):
        order_lines_kits = order_lines.filtered('of_is_kit')
        field_used = self.cost_method
        for line in order_lines_kits:
            for kit_line in line.kit_id.kit_line_ids:
                cost = kit_line.product_id[field_used]
                if self.real_cost and kit_line.procurement_ids:
                    purchase_lines = kit_line.procurement_ids.mapped('move_ids.move_orig_ids.purchase_line_id')
                    purchase_lines |= kit_line.procurement_ids.mapped('move_ids.purchase_line_id')
                    purchase_qty = sum(purchase_lines.mapped('product_qty'))
                    if purchase_qty:
                        purchase_price_subtotal = sum(purchase_lines.mapped('price_subtotal'))
                        purchase_unit_price = purchase_price_subtotal / purchase_qty if purchase_qty else 0.0
                        cost = purchase_unit_price * line.product_id.property_of_purchase_coeff
                if self.exclude_change_zero and not cost:
                    continue
                kit_line.cost_unit = cost
            line.purchase_price = line.cost_comps
        super(OFCostRecomputeWizard, self)._handle_order_lines(order_lines - order_lines_kits)
