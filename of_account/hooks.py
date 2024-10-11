# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _set_account_journal_restrict_mode_hash_table(env):
    # Set the value of `restrict_mode_hash_table` field on account.journal depending on the type of the journal.
    journal_sale = env["account.journal"].search([("type", "in", ["sale", "bank", "cash"])])
    journal_sale.write({"restrict_mode_hash_table": True})
    # Ensure that the value is False for the other types
    journal_purchase = env["account.journal"].search([("type", "in", ["purchase", "general"])])
    journal_purchase.write({"restrict_mode_hash_table": False})


def _update_sales_warnings(cr, env):
    cr.execute("SELECT id FROM res_partner WHERE invoice_warn != 'no-message'")
    partnes_with_warning_ids = cr.fetchall()
    cr.execute("SELECT id FROM res_partner WHERE invoice_warn = 'block'")
    partner_blocked_ids = cr.fetchall()
    partnes_with_warning_ids = tuple(map(lambda e: e[0], partnes_with_warning_ids))
    partner_blocked_ids = tuple(map(lambda e: e[0], partner_blocked_ids))
    if partnes_with_warning_ids:
        cr.execute("UPDATE res_partner SET of_is_account_warn = 't' WHERE id IN %s", (partnes_with_warning_ids,))
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
    _set_account_journal_restrict_mode_hash_table(env)
    _update_sales_warnings(cr, env)
