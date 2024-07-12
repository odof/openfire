# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _create_invoices_directory(cr, env):
    # pour chaque dossier partenaire, on ajoute un sous-dossier Invoices & Refunds
    partners = env["res.partner"].search([("user_ids", "=", False)])
    partners.create_invoices_directory()


def _create_invoices_files(cr, env):
    # pour chaque sale order, on ajoute les pièces jointes qui peuvent déjà exister
    file_obj = env["dms.file"]
    move_obj = env["account.move"]
    customer_invoices = move_obj.search([("move_type", "in", ["out_invoice", "out_refund"])])
    vendor_invoices = move_obj.search([("move_type", "in", ["in_invoice", "in_refund"])])
    file_obj.create_dms_files("account.move", customer_invoices.ids, "partner_id", "Customer Invoices & Refunds", "OUT")
    file_obj.create_dms_files("account.move", vendor_invoices.ids, "partner_id", "Vendor Invoices & Refunds", "IN")


def _create_virtual_file_reports(cr, env):
    # pour chaque company, on ajoute le rapport par défaut des fichiers virtuels
    value = {
        "model_id": env.ref("account.model_account_move").id,
        "report_id": env.ref("account.account_invoices").id,
    }
    cr.execute("select id from res_company")

    for company_id in cr.fetchall():
        value["company_id"] = company_id
        env["of.dms.virtual_file_report"].create(value)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _create_virtual_file_reports(cr, env)
    _create_invoices_directory(cr, env)
    _create_invoices_files(cr, env)
