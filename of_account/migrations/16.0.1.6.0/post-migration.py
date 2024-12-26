# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    posted_moves = env["account.move"].search([("state", "=", "posted")])
    posted_moves.of_update_down_payment()
