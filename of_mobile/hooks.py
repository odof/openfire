# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _set_default_of_mobile_auto_publish_service(env):
    settings = env['res.config.settings'].create({'of_mobile_auto_publish_service': True})
    settings.execute()


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_default_of_mobile_auto_publish_service(env)
