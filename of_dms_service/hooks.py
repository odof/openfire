# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _create_services_directory(cr, env):
    # pour chaque dossier partenaire, on ajoute un sous-dossier DI
    partners = env["res.partner"].search([("user_ids", "=", False)])
    partners.create_services_directory()


def _create_services_files(cr, env):
    # pour chaque service order, on ajoute les pièces jointes qui peuvent déjà exister
    services = env["of.service.request"].search([])
    env["dms.file"].create_dms_files("of.service.request", services.ids, "partner_id", "Service Requests")


def _create_virtual_file_reports(cr, env):
    # pour chaque company, on ajoute le rapport par défaut des fichiers virtuels
    value = {
        "model_id": env.ref("of_service.model_of_service_request").id,
        "report_id": env.ref("of_service.action_report_service_request").id,
    }
    cr.execute("select id from res_company")

    for company_id in cr.fetchall():
        value["company_id"] = company_id
        env["of.dms.virtual_file_report"].create(value)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _create_virtual_file_reports(cr, env)
    _create_services_directory(cr, env)
    _create_services_files(cr, env)
