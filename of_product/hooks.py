# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo.tools import float_is_zero

from odoo.addons.stock_account.models.stock_move import StockMove


def post_init_hook(cr, registry):
    """🐒-patch of standard methods.
    Trick to avoid to override standard methods when the module is not installed.

    We are 🐒-patching the following methods:
    - stock.move.product_price_update_before_done()
    """

    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(
            lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average'
        ):
            product_tot_qty_available = (
                move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            )
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )

            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            elif float_is_zero(
                product_tot_qty_available + move.product_qty, precision_rounding=rounding
            ) or float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            else:
                # Get the standard price
                amount_unit = (
                    std_price_update.get((move.company_id.id, move.product_id.id))
                    or move.product_id.with_company(move.company_id).standard_price
                )
                new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (
                    product_tot_qty_available + qty
                )

            tmpl_dict[move.product_id.id] += qty_done
            if move.product_id.categ_id.of_stock_update_standard_price:
                # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write
                # on products
                move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                    {'standard_price': new_std_price}
                )
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(
            lambda move: move.with_company(move.company_id).product_id.cost_method == 'fifo'
            and float_is_zero(move.product_id.sudo().quantity_svl, precision_rounding=move.product_id.uom_id.rounding)
        ):
            if move.product_id.categ_id.of_stock_update_standard_price:
                move.product_id.with_company(move.company_id.id).sudo().write(
                    {'standard_price': move._get_price_unit()}
                )

    # Patch product_price_update_before_done method
    if not hasattr(StockMove, 'product_price_update_before_done_original'):
        StockMove.product_price_update_before_done_original = StockMove.product_price_update_before_done
    StockMove._patch_method('product_price_update_before_done', product_price_update_before_done)


def uninstall_hook(cr, registry):
    """Restore original methods"""
    StockMove._revert_method('product_price_update_before_done')
    delattr(StockMove, 'product_price_update_before_done_original')
