# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    config_params = [
        "wizville_sftp_host",
        "wizville_sftp_port",
        "wizville_sftp_user",
        "wizville_sftp_password",
        "wizville_sftp_deposit_directory",
        "wizville_sftp_pickup_directory",
    ]
    env["ir.config_parameter"].search([("key", "in", config_params)]).unlink()
