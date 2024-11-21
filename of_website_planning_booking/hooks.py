# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _set_default_of_website_planning_booking_settings(env):
    website = env["website"].search([], limit=1)
    days = env["of.days"].sudo().search([("number", "in", (1, 2, 3, 4, 5))], order="number")

    settings = env["res.config.settings"].create(
        {
            "of_booking_open_new_customer": True,
            "of_booking_use_partner_company": True,
            "of_booking_intervention_company_id": website.company_id.id,
            "of_booking_opened_day_ids_str": ",".join(days.mapped(lambda x: str(x.id))),
            "of_booking_open_days_number": 60,
            "of_booking_search_mode": "oneway",
            "of_booking_search_type": "distance",
            "of_booking_search_max_criteria": 20,
            "of_booking_allow_empty_days": True,
            "of_booking_intervention_state": "draft",
            "of_booking_display_price": True,
            "of_booking_morning_hours_label": "8h00 - 13h00",
            "of_booking_afternoon_hours_label": "14h00 - 18h00",
        }
    )

    settings.execute()


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_default_of_website_planning_booking_settings(env)
