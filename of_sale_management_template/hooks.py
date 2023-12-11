# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env['res.config.settings'].create(
        {
            'group_sale_order_template': True,
        }
    ).execute()


def _uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    env['res.config.settings'].create(
        {
            'group_sale_order_template': False,
        }
    ).execute()
