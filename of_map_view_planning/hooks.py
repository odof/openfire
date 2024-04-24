# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _post_init_hook(cr, registry):
    """Add map from following action"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref('of_planning.action_calendar_event')
    view_modes = action.view_mode.split(',')
    if 'map' not in view_modes:
        view_modes.append('map')
        action.view_mode = ','.join(view_modes)

    action = env.ref('of_planning.action_report_intervention_report')
    view_modes = action.binding_view_types.split(',')
    if 'map' not in view_modes:
        view_modes.append('map')
        action.binding_view_types = ','.join(view_modes)

    action = env.ref('of_planning.action_report_intervention_sheet')
    view_modes = action.binding_view_types.split(',')
    if 'map' not in view_modes:
        view_modes.append('map')
        action.binding_view_types = ','.join(view_modes)

    action = env.ref('of_planning.action_of_planning_intervention_generate_invoice_tree_view')
    view_modes = action.binding_view_types.split(',')
    if 'map' not in view_modes:
        view_modes.append('map')
        action.binding_view_types = ','.join(view_modes)

    action = env.ref('of_planning.action_of_planning_intervention_generate_delivery')
    view_modes = action.binding_view_types.split(',')
    if 'map' not in view_modes:
        view_modes.append('map')
        action.binding_view_types = ','.join(view_modes)


def _uninstall_hook(cr, registry):
    """Remove map from modified action"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref('of_planning.action_calendar_event')
    view_modes = action.view_mode.split(',')
    if 'map' in view_modes:
        view_modes.remove('map')
        action.view_mode = ','.join(view_modes)

    action = env.ref('of_planning.action_report_intervention_report')
    view_modes = action.binding_view_types.split(',')
    if 'map' in view_modes:
        view_modes.remove('map')
        action.binding_view_types = ','.join(view_modes)

    action = env.ref('of_planning.action_report_intervention_sheet')
    view_modes = action.binding_view_types.split(',')
    if 'map' in view_modes:
        view_modes.remove('map')
        action.binding_view_types = ','.join(view_modes)

    action = env.ref('of_planning.action_of_planning_intervention_generate_invoice_tree_view')
    view_modes = action.binding_view_types.split(',')
    if 'map' in view_modes:
        view_modes.remove('map')
        action.binding_view_types = ','.join(view_modes)

    action = env.ref('of_planning.action_of_planning_intervention_generate_delivery')
    view_modes = action.binding_view_types.split(',')
    if 'map' in view_modes:
        view_modes.remove('map')
        action.binding_view_types = ','.join(view_modes)
