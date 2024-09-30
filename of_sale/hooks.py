# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _set_default_of_color_bg_section(env):
    if not env["ir.config_parameter"].sudo().get_param("of.sale.report.account.move.of_color_bg_section"):
        env["ir.config_parameter"].sudo().set_param("of.sale.report.account.move.of_color_bg_section", "#f0f0f0")


def _set_default_of_color_font(env):
    if not env["ir.config_parameter"].sudo().get_param("of.sale.report.account.move.of_color_font"):
        env["ir.config_parameter"].sudo().set_param("of.sale.report.account.move.of_color_font", "#000000")


def _empty_product_category_margin_rate(env):
    env["ir.config_parameter"].sudo().set_param("sale.default_deposit_product_id", False)


def _update_sales_warnings(cr, env):
    cr.execute("SELECT id FROM res_partner WHERE sale_warn != 'no-message'")
    partnes_with_warning_ids = cr.fetchall()
    cr.execute("SELECT id FROM res_partner WHERE sale_warn = 'block'")
    partner_blocked_ids = cr.fetchall()
    partnes_with_warning_ids = tuple(map(lambda e: e[0], partnes_with_warning_ids))
    partner_blocked_ids = tuple(map(lambda e: e[0], partner_blocked_ids))
    if partnes_with_warning_ids:
        cr.execute("UPDATE res_partner SET of_is_sale_warn = 't' WHERE id IN %s", (partnes_with_warning_ids,))
        cr.execute("UPDATE res_partner SET of_is_warn = 't' WHERE id IN %s", (partnes_with_warning_ids,))
        cr.execute(
            "UPDATE res_partner SET invoice_warn_msg = sale_warn_msg "
            "WHERE (invoice_warn_msg IS NULL OR invoice_warn_msg = '') and id IN %s",
            (partnes_with_warning_ids,),
        )
        cr.execute(
            "UPDATE res_partner SET invoice_warn_msg = sale_warn_msg "
            "WHERE (invoice_warn_msg IS NULL OR invoice_warn_msg = '') and id IN %s",
            (partnes_with_warning_ids,),
        )
    if partner_blocked_ids:
        cr.execute("UPDATE res_partner SET of_warn_block = 't' WHERE id in %s", (partner_blocked_ids,))


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_default_of_color_bg_section(env)
    _set_default_of_color_font(env)
    # _empty_product_category_margin_rate(env)  TODO: uncomment me when the module is ready and if keeping this feature
    _update_sales_warnings(cr, env)
