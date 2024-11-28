# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # To avoid upgrade issues, we deactivate the view during the update process and reactivate it after
    view = env["ir.ui.view"].search([("name", "=", "of.sale.res.config.settings.view.form.inherit")])
    view.active = False
