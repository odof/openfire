# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _init_planning_config(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].search([])
    for company in companies:
        company.of_planning_start_hour = 6
        company.of_planning_end_hour = 20


def post_init_hook(cr, registry):
    _init_planning_config(cr)
