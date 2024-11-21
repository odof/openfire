# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.of_planning_tour.models.res_config_settings import SELECTION_SEARCH_MODES, SELECTION_SEARCH_TYPES


class ResCompany(models.Model):
    _inherit = "res.company"

    of_booking_specific = fields.Boolean(
        string="Planning booking - Specific configuration for this company",
    )
    of_booking_opened_day_ids = fields.Many2many(
        comodel_name="of.days",
        relation="res_company_booking_days_rel",
        string="Planning booking - Opened days",
    )
    of_booking_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="res_company_booking_employee_rel",
        string="Planning booking - Available operators",
        domain=["|", ("of_is_operator", "=", True), ("of_is_salesperson", "=", True)],
    )
    of_booking_open_days_number = fields.Integer(
        string="Planning booking - Number of opened days",
    )
    of_booking_search_mode = fields.Selection(
        selection=SELECTION_SEARCH_MODES,
        string="Planning booking - Search mode",
    )
    of_booking_search_type = fields.Selection(
        selection=SELECTION_SEARCH_TYPES,
        string="Planning booking - Search type",
    )
    of_booking_search_max_criteria = fields.Integer(
        string="Planning booking - Search max criterion",
    )
    of_booking_allow_empty_days = fields.Boolean(
        string="Planning booking - Allow booking on empty days",
        default=True,
    )
    of_booking_empty_days_search_type = fields.Selection(
        selection=SELECTION_SEARCH_TYPES,
        string="Planning booking - Search type for empty days",
    )
    of_booking_empty_days_search_max_criteria = fields.Integer(
        string="Planning booking - Search max criterion for empty days",
    )
    of_booking_intervention_state = fields.Selection(
        selection=[("draft", "Draft"), ("confirmed", "Confirmed")],
        string="Planning booking - Interventions state",
        default="draft",
    )
    of_booking_display_price = fields.Boolean(
        string="Planning booking - Display service price",
        default=True,
    )
    of_booking_terms_file = fields.Binary(
        string="Planning booking - PDF file for General Terms and Conditions",
    )
    of_booking_terms_filename = fields.Char(
        string="Planning booking - PDF file name for General Terms and Conditions",
    )
    of_booking_morning_hours_label = fields.Char(
        string="Planning booking - Morning hours label",
    )
    of_booking_afternoon_hours_label = fields.Char(
        string="Planning booking - Afternoon hours label",
    )
    of_booking_validation_note = fields.Html(
        string="Planning booking - Intervention confirmation notes",
    )
