# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners_wo_of_company_name = env["res.partner"].search(
        [("of_company_name", "=", False), ("is_company", "=", True)]
    )
    for partner in partners_wo_of_company_name:
        partner.of_company_name = partner.name
