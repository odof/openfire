# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _create_pickings_directory(cr, env):
    # pour chaque dossier partenaire, on ajoute un sous-dossier Sales
    partners = env["res.partner"].search([("user_ids", "=", False)])
    partners.create_pickings_directory()


def _create_pickings_files(cr, env):
    # pour chaque picking order, on ajoute les pièces jointes qui peuvent déjà exister
    file_obj = env["dms.file"]
    picking_obj = env["stock.picking"]
    pickings = picking_obj.search([("picking_type_code", "=", "outgoing")])
    receipts = picking_obj.search([("picking_type_code", "=", "incoming")])
    file_obj.create_dms_files("stock.picking", pickings.ids, "partner_id", "Delivery Slips", "outgoing")
    file_obj.create_dms_files("stock.picking", receipts.ids, "partner_id", "Receipt Slips", "incoming")


def _create_virtual_file_reports(cr, env):
    # pour chaque company, on ajoute le rapport par défaut des fichiers virtuels
    value = {
        "model_id": env.ref("stock.model_stock_picking").id,
        "report_id": env.ref("stock.action_report_delivery").id,
    }
    cr.execute("select id from res_company")

    for company_id in cr.fetchall():
        value["company_id"] = company_id
        env["of.dms.virtual_file_report"].create(value)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _create_virtual_file_reports(cr, env)
    _create_pickings_directory(cr, env)
    _create_pickings_files(cr, env)
