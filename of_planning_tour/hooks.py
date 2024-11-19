# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api, fields

_logger = logging.getLogger(__name__)


def _init_tour_settings(env):
    icp_obj = env["ir.config_parameter"]

    if not icp_obj.get_param("of.planning.tour.company_choice"):
        icp_obj.set_param("of.planning.tour.company_choice", "contact")
    if not icp_obj.get_param("of.planning.tour.search_type"):
        icp_obj.set_param("of.planning.tour.search_mode", "oneway_or_return")
    if not icp_obj.get_param("of.planning.tour.search_type"):
        icp_obj.set_param("of.planning.tour.search_type", "distance")
    if not icp_obj.get_param("of.planning.tour.nbr_months_tour_creation"):
        icp_obj.set_param("of.planning.tour.nbr_months_tour_creation", 18)
    if not icp_obj.get_param("of.planning.tour.tour_minimum_free_slot_duration"):
        icp_obj.set_param("of.planning.tour.tour_minimum_free_slot_duration", 0.5)


def _init_tours(env):
    # Create tours from employees
    env["of.planning.tour"].cron_generate_employees_tours()
    # Create tours from events
    events = env["calendar.event"].search([("start", ">=", fields.Date.today()), ("of_employee_ids", "!=", False)])
    events.action_create_tours()
    tours = env["of.planning.tour"].search([("date", ">=", fields.Date.today())])
    try:
        tours.action_compute_osrm_data()
    except Exception as e:
        _logger.info(f"Error while computing OSRM data during module installation : {e}")


def _init_available_slot_from_tour(env):
    employees = env["hr.employee"].search([])
    tours = env["of.planning.tour"].search([("date", ">=", fields.Date.today()), ("employee_id", "in", employees.ids)])
    tours._reorganize_available_slot()


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _init_tour_settings(env)
    _init_tours(env)
    _init_available_slot_from_tour(env)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    icp_obj = env["ir.config_parameter"]

    # Delete the created ir.config.parameter
    icp_obj.sudo().search([("key", "like", "of.planning.tour.%")]).unlink()
