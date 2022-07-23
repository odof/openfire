# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api
from odoo.addons.stock_account.models.stock import StockMove


@api.multi
def product_price_update_before_done(self):
    tmpl_dict = defaultdict(lambda: 0.0)
    # adapt standard price on incomming moves if the product cost_method is 'average'
    std_price_update = {}
    for move in self.filtered(lambda move: move.location_id.usage in ('supplier', 'production') and move.product_id.cost_method == 'average'):
        product_tot_qty_available = move.product_id.qty_available + tmpl_dict[move.product_id.id]

        # if the incoming move is for a purchase order with foreign currency, need to call this to get the same value that the quant will use.
        if product_tot_qty_available <= 0:
            new_std_price = move.get_price_unit()
        else:
            # Get the standard price
            amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.standard_price
            new_std_price = ((amount_unit * product_tot_qty_available) + (move.get_price_unit() * move.product_qty)) / (product_tot_qty_available + move.product_qty)

        tmpl_dict[move.product_id.id] += move.product_qty
        if move.product_id.categ_id.of_stock_update_standard_price:
            # Write the standard price, as SUPERUSER_ID because a warehouse manager
            # may not have the right to write on products
            move.product_id.with_context(force_company=move.company_id.id).sudo().write(
                {'standard_price': new_std_price})
        std_price_update[move.company_id.id, move.product_id.id] = new_std_price


def _store_average_cost_price(self):
    """ Store the average price of the move on the move and product form (costing method 'real')"""
    for move in self.filtered(lambda move: move.product_id.cost_method == 'real'):
        # product_obj = self.pool.get('product.product')
        if any(q.qty <= 0 for q in move.quant_ids) or move.product_qty == 0:
            # if there is a negative quant, the standard price shouldn't be updated
            continue
        # Note: here we can't store a quant.cost directly as we may have moved out 2 units
        # (1 unit to 5€ and 1 unit to 7€) and in case of a product return of 1 unit, we can't
        # know which of the 2 costs has to be used (5€ or 7€?). So at that time, thanks to the
        # average valuation price we are storing we will valuate it at 6€
        valuation_price = sum(q.qty * q.cost for q in move.quant_ids)
        average_valuation_price = valuation_price / move.product_qty

        if move.product_id.categ_id.of_stock_update_standard_price:
            move.product_id.with_context(force_company=move.company_id.id).sudo().write(
                {'standard_price': average_valuation_price})
        move.write({'price_unit': average_valuation_price})


StockMove.product_price_update_before_done = product_price_update_before_done
StockMove._store_average_cost_price = _store_average_cost_price
