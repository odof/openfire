# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _update_real_file_type(cr, env):
    dms_files = env["dms.file"].search([("of_type", "=", False)])
    dms_files.write({"of_type": "real"})


def _create_partners_directory(cr, env):
    partners = env["res.partner"].search([("user_ids", "=", False)])
    partners.create_partners_directory()


def post_init_hook(cr, registry):
    """Migrate data from old fields to new ones."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    _update_real_file_type(cr, env)
    _create_partners_directory(cr, env)
