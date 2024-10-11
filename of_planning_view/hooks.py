# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry):
    """Remove planning from modified action"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    action = env.ref("of_planning.action_calendar_event")
    view_modes = action.view_mode.split(",")
    view_modes.remove("planning")
    action.view_mode = ",".join(view_modes)
