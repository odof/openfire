# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _create_leads_directory(cr, env):
    # pour chaque dossier partenaire, on ajoute un sous-dossier leads
    partners = env["res.partner"].search([("user_ids", "=", False)])
    partners.create_leads_directory()


def _create_leads_files(cr, env):
    # pour chaque opportunité, on ajoute les pièces jointes qui peuvent déjà exister
    leads = env["crm.lead"].search([])
    env["dms.file"].create_dms_files("crm.lead", leads.ids, "partner_id", "Leads")


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _create_leads_directory(cr, env)
    _create_leads_files(cr, env)
