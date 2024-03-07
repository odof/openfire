# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _uninstall_hook(cr, registry):
    """Remove map from modified action"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref('account.res_partner_action_customer')
    view_modes = action.view_mode.split(',')
    view_modes.remove('map')
    action.view_mode = ','.join(view_modes)

    action = env.ref('account.res_partner_action_supplier')
    view_modes = action.view_mode.split(',')
    view_modes.remove('map')
    action.view_mode = ','.join(view_modes)
