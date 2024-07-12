# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _create_interventions_directory(cr, env):
    # pour chaque dossier partenaire, on ajoute un sous-dossier interventions
    partners = env["res.partner"].search([("user_ids", "=", False)])
    partners.create_interventions_directory()


def _create_interventions_files(cr, env):
    # pour chaque intervention order, on ajoute les pièces jointes qui peuvent déjà exister
    interventions = env["calendar.event"].search([("of_type", "=", "intervention")])
    env["dms.file"].create_dms_files("calendar.event", interventions.ids, "of_partner_id", "Interventions")


def _create_virtual_file_reports(cr, env):
    file_report_obj = env["of.dms.virtual_file_report"]
    # pour chaque company, on ajoute le rapport par défaut des fichiers virtuels
    report_value = {
        "model_id": env.ref("calendar.model_calendar_event").id,
        "report_id": env.ref("of_planning.action_report_intervention_report").id,
    }
    sheet_value = {
        "model_id": env.ref("calendar.model_calendar_event").id,
        "report_id": env.ref("of_planning.action_report_intervention_sheet").id,
    }
    cr.execute("select id from res_company")
    for company_id in cr.fetchall():
        report_value["company_id"] = company_id
        sheet_value["company_id"] = company_id
        file_report_obj.create(report_value)
        file_report_obj.create(sheet_value)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _create_virtual_file_reports(cr, env)
    _create_interventions_directory(cr, env)
    _create_interventions_files(cr, env)
