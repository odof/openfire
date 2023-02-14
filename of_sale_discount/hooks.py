# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID


def _set_of_discount_formula_on_sale_order(cr):
    cr.execute(
        "UPDATE sale_order_line "
        "SET of_discount_formula = TEXT(discount) "
        "WHERE of_discount_formula IS NULL AND discount != 0")


def _set_of_discount_formula_on_pricelist_item(cr):
    cr.execute(
        "UPDATE product_pricelist_item "
        "SET of_percent_price_formula = TEXT(percent_price) "
        "WHERE of_percent_price_formula IS NULL AND percent_price != 0")


def _set_of_discount_formula_on_move_line(cr):
    cr.execute(
        "UPDATE account_move_line "
        "SET of_discount_formula = TEXT(discount) "
        "WHERE of_discount_formula IS NULL AND discount != 0")


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_of_discount_formula_on_sale_order(env.cr)
    _set_of_discount_formula_on_pricelist_item(env.cr)
    _set_of_discount_formula_on_move_line(env.cr)
