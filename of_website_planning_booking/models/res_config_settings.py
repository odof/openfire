# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.of_planning_tour.models.res_config_settings import SELECTION_SEARCH_MODES, SELECTION_SEARCH_TYPES


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_booking_open_new_customer = fields.Boolean(
        string="(OF) Allow new customers",
        config_parameter="of.website.planning.booking.open_new_customer",
    )
    of_booking_use_partner_company = fields.Boolean(
        string="(OF) Use partner company for existing customers",
        config_parameter="of.website.planning.booking.use_partner_company",
    )
    of_booking_intervention_company_id = fields.Many2one(
        comodel_name="res.company",
        string="(OF) Intervention company",
        config_parameter="of.website.planning.booking.intervention_company_id",
    )
    of_booking_company_specific = fields.Boolean(
        string="(OF) Specific configuration for this company",
        related="company_id.of_booking_specific",
        readonly=False,
    )
    of_booking_opened_day_ids = fields.Many2many(
        comodel_name="of.days",
        string="(OF) Opened days",
        compute="_compute_of_booking_opened_day_ids",
        inverse="_inverse_of_booking_opened_day_ids",
        help="Allow booking for these days only",
    )
    of_booking_opened_day_ids_str = fields.Char(
        string="(OF) Opened days in String",
        config_parameter="of.website.planning.booking.opened_day_ids",
        help="Technical field to store M2M fields into a config parameter. As config_parameters does not accept m2m "
        "field, we store the fields with a comma separated string into a Char config field.",
    )
    of_booking_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="(OF) Available operators",
        compute="_compute_of_booking_employee_ids",
        inverse="_inverse_of_booking_employee_ids",
        domain=["|", ("of_is_operator", "=", True), ("of_is_salesperson", "=", True)],
        help="Allow booking for these operators only",
    )
    of_booking_employee_ids_str = fields.Char(
        string="(OF) Available operators in String",
        config_parameter="of.website.planning.booking.employee_ids",
        help="Technical field to store M2M fields into a config parameter. As config_parameters does not accept m2m "
        "field, we store the fields with a comma separated string into a Char config field.",
    )
    of_booking_open_days_number = fields.Integer(
        string="(OF) Number of opened days",
        compute="_compute_of_booking_open_days_number",
        inverse="_inverse_of_booking_open_days_number",
    )
    of_booking_search_mode = fields.Selection(
        selection=SELECTION_SEARCH_MODES,
        string="(OF) Search mode",
        compute="_compute_of_booking_search_mode",
        inverse="_inverse_of_booking_search_mode",
        required=True,
    )
    of_booking_search_type = fields.Selection(
        selection=SELECTION_SEARCH_TYPES,
        string="(OF) Search type",
        compute="_compute_of_booking_search_type",
        inverse="_inverse_of_booking_search_type",
        required=True,
    )
    of_booking_search_max_criteria = fields.Integer(
        string="(OF) Search max criterion",
        compute="_compute_of_booking_search_max_criteria",
        inverse="_inverse_of_booking_search_max_criteria",
    )
    of_booking_allow_empty_days = fields.Boolean(
        string="(OF) Allow booking on empty days",
        compute="_compute_of_booking_allow_empty_days",
        inverse="_inverse_of_booking_allow_empty_days",
    )
    of_booking_empty_days_search_type = fields.Selection(
        selection=SELECTION_SEARCH_TYPES,
        string="(OF) Search type for empty days",
        compute="_compute_of_booking_empty_days_search_type",
        inverse="_inverse_of_booking_empty_days_search_type",
        required=True,
    )
    of_booking_empty_days_search_max_criteria = fields.Integer(
        string="(OF) Search max criterion for empty days",
        compute="_compute_of_booking_empty_days_search_max_criteria",
        inverse="_inverse_of_booking_empty_days_search_max_criteria",
    )
    of_booking_intervention_state = fields.Selection(
        selection=[("draft", "Draft"), ("confirmed", "Confirmed")],
        string="(OF) Interventions state",
        compute="_compute_of_booking_intervention_state",
        inverse="_inverse_of_booking_intervention_state",
        required=True,
    )
    of_booking_display_price = fields.Boolean(
        string="(OF) Display service price",
        compute="_compute_of_booking_display_price",
        inverse="_inverse_of_booking_display_price",
    )
    of_booking_terms_file = fields.Binary(
        string="(OF) PDF file for General Terms and Conditions",
        compute="_compute_of_booking_terms_file",
        inverse="_inverse_of_booking_terms_file",
    )
    of_booking_terms_filename = fields.Char(
        string="(OF) PDF file name for General Terms and Conditions",
        compute="_compute_of_booking_terms_file",
        inverse="_inverse_of_booking_terms_filename",
    )
    of_booking_morning_hours_label = fields.Char(
        string="(OF) Morning hours label",
        compute="_compute_of_booking_morning_hours_label",
        inverse="_inverse_of_booking_morning_hours_label",
    )
    of_booking_afternoon_hours_label = fields.Char(
        string="(OF) Afternoon hours label",
        compute="_compute_of_booking_afternoon_hours_label",
        inverse="_inverse_of_booking_afternoon_hours_label",
    )
    of_booking_validation_note = fields.Html(
        string="(OF) Intervention confirmation notes",
        compute="_compute_of_booking_validation_note",
        inverse="_inverse_of_booking_validation_note",
    )

    @api.constrains("of_booking_open_days_number")
    def _check_of_booking_open_days_number(self):
        for setting in self:
            if setting.of_booking_open_days_number < 0 or setting.of_booking_open_days_number > 180:
                raise ValidationError(_("The number of opened days for booking must be positive and can't exceed 180."))

    @api.depends("of_booking_company_specific", "company_id.of_booking_opened_day_ids", "of_booking_opened_day_ids_str")
    def _compute_of_booking_opened_day_ids(self):
        days_obj = self.env["of.days"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_opened_day_ids = setting.company_id.of_booking_opened_day_ids
            elif setting.of_booking_opened_day_ids_str:
                ids = setting.of_booking_opened_day_ids_str.split(",")
                ids = [int(id) for id in ids if id.isdigit()]
                setting.of_booking_opened_day_ids = days_obj.search([("id", "in", ids)])
            else:
                setting.of_booking_opened_day_ids = None

    def _inverse_of_booking_opened_day_ids(self):
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_opened_day_ids = setting.of_booking_opened_day_ids
            elif setting.of_booking_opened_day_ids:
                setting.of_booking_opened_day_ids_str = ",".join(
                    setting.of_booking_opened_day_ids.mapped(lambda x: str(x.id))
                )
            else:
                setting.of_booking_opened_day_ids_str = ""

    @api.depends("of_booking_company_specific", "company_id.of_booking_employee_ids", "of_booking_employee_ids_str")
    def _compute_of_booking_employee_ids(self):
        employee_obj = self.env["hr.employee"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_employee_ids = setting.company_id.of_booking_employee_ids
            elif setting.of_booking_employee_ids_str:
                ids = setting.of_booking_employee_ids_str.split(",")
                ids = [int(id) for id in ids if id.isdigit()]
                setting.of_booking_employee_ids = employee_obj.search([("id", "in", ids)])
            else:
                setting.of_booking_employee_ids = None

    def _inverse_of_booking_employee_ids(self):
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_employee_ids = setting.of_booking_employee_ids
            elif setting.of_booking_employee_ids:
                setting.of_booking_employee_ids_str = ",".join(
                    setting.of_booking_employee_ids.mapped(lambda x: str(x.id))
                )
            else:
                setting.of_booking_employee_ids_str = ""

    @api.depends("of_booking_company_specific", "company_id.of_booking_open_days_number")
    def _compute_of_booking_open_days_number(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_open_days_number = setting.company_id.of_booking_open_days_number
            else:
                setting.of_booking_open_days_number = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.open_days_number"
                )

    def _inverse_of_booking_open_days_number(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_open_days_number = setting.of_booking_open_days_number
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.open_days_number", setting.of_booking_open_days_number
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_search_mode")
    def _compute_of_booking_search_mode(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_search_mode = setting.company_id.of_booking_search_mode
            else:
                setting.of_booking_search_mode = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.search_mode"
                )

    def _inverse_of_booking_search_mode(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_search_mode = setting.of_booking_search_mode
            else:
                config_param_obj.set_param("of.website.planning.booking.search_mode", setting.of_booking_search_mode)

    @api.depends("of_booking_company_specific", "company_id.of_booking_search_type")
    def _compute_of_booking_search_type(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_search_type = setting.company_id.of_booking_search_type
            else:
                setting.of_booking_search_type = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.search_type"
                )

    def _inverse_of_booking_search_type(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_search_type = setting.of_booking_search_type
            else:
                config_param_obj.set_param("of.website.planning.booking.search_type", setting.of_booking_search_type)

    @api.depends("of_booking_company_specific", "company_id.of_booking_search_max_criteria")
    def _compute_of_booking_search_max_criteria(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_search_max_criteria = setting.company_id.of_booking_search_max_criteria
            else:
                setting.of_booking_search_max_criteria = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.search_max_criteria"
                )

    def _inverse_of_booking_search_max_criteria(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_search_max_criteria = setting.of_booking_search_max_criteria
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.search_max_criteria", setting.of_booking_search_max_criteria
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_allow_empty_days")
    def _compute_of_booking_allow_empty_days(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_allow_empty_days = setting.company_id.of_booking_allow_empty_days
            else:
                setting.of_booking_allow_empty_days = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.allow_empty_days"
                )

    def _inverse_of_booking_allow_empty_days(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_allow_empty_days = setting.of_booking_allow_empty_days
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.allow_empty_days", setting.of_booking_allow_empty_days
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_empty_days_search_type")
    def _compute_of_booking_empty_days_search_type(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_empty_days_search_type = setting.company_id.of_booking_empty_days_search_type
            else:
                setting.of_booking_empty_days_search_type = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.empty_days_search_type"
                )

    def _inverse_of_booking_empty_days_search_type(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_empty_days_search_type = setting.of_booking_empty_days_search_type
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.empty_days_search_type", setting.of_booking_empty_days_search_type
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_empty_days_search_max_criteria")
    def _compute_of_booking_empty_days_search_max_criteria(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_empty_days_search_max_criteria = (
                    setting.company_id.of_booking_empty_days_search_max_criteria
                )
            else:
                setting.of_booking_empty_days_search_max_criteria = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.empty_days_search_max_criteria"
                )

    def _inverse_of_booking_empty_days_search_max_criteria(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_empty_days_search_max_criteria = (
                    setting.of_booking_empty_days_search_max_criteria
                )
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.empty_days_search_max_criteria",
                    setting.of_booking_empty_days_search_max_criteria,
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_intervention_state")
    def _compute_of_booking_intervention_state(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_intervention_state = setting.company_id.of_booking_intervention_state
            else:
                setting.of_booking_intervention_state = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.intervention_state"
                )

    def _inverse_of_booking_intervention_state(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_intervention_state = setting.of_booking_intervention_state
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.intervention_state", setting.of_booking_intervention_state
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_display_price")
    def _compute_of_booking_display_price(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_display_price = setting.company_id.of_booking_display_price
            else:
                setting.of_booking_display_price = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.display_price"
                )

    def _inverse_of_booking_display_price(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_display_price = setting.of_booking_display_price
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.display_price", setting.of_booking_display_price
                )

    @api.depends(
        "of_booking_company_specific",
        "company_id.of_booking_terms_file",
        "company_id.of_booking_terms_file",
        "website_id.company_id.of_booking_terms_file",
        "website_id.company_id.of_booking_terms_filename",
    )
    def _compute_of_booking_terms_file(self):
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_terms_file = setting.company_id.of_booking_terms_file
                setting.of_booking_terms_filename = setting.company_id.of_booking_terms_filename
            else:
                setting.of_booking_terms_file = setting.website_id.company_id.of_booking_terms_file
                setting.of_booking_terms_filename = setting.website_id.company_id.of_booking_terms_filename

    def _inverse_of_booking_terms_file(self):
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_terms_file = setting.of_booking_terms_file
            else:
                setting.website_id.company_id.of_booking_terms_file = setting.of_booking_terms_file

    def _inverse_of_booking_terms_filename(self):
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_terms_filename = setting.of_booking_terms_filename
            else:
                setting.website_id.company_id.of_booking_terms_filename = setting.of_booking_terms_filename

    @api.depends("of_booking_company_specific", "company_id.of_booking_morning_hours_label")
    def _compute_of_booking_morning_hours_label(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_morning_hours_label = setting.company_id.of_booking_morning_hours_label
            else:
                setting.of_booking_morning_hours_label = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.morning_hours_label"
                )

    def _inverse_of_booking_morning_hours_label(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_morning_hours_label = setting.of_booking_morning_hours_label
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.morning_hours_label", setting.of_booking_morning_hours_label
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_afternoon_hours_label")
    def _compute_of_booking_afternoon_hours_label(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_afternoon_hours_label = setting.company_id.of_booking_afternoon_hours_label
            else:
                setting.of_booking_afternoon_hours_label = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.afternoon_hours_label"
                )

    def _inverse_of_booking_afternoon_hours_label(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_afternoon_hours_label = setting.of_booking_afternoon_hours_label
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.afternoon_hours_label", setting.of_booking_afternoon_hours_label
                )

    @api.depends("of_booking_company_specific", "company_id.of_booking_validation_note")
    def _compute_of_booking_validation_note(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.of_booking_validation_note = setting.company_id.of_booking_validation_note
            else:
                setting.of_booking_validation_note = config_param_obj.sudo().get_param(
                    "of.website.planning.booking.validation_note"
                )

    def _inverse_of_booking_validation_note(self):
        config_param_obj = self.env["ir.config_parameter"]
        for setting in self:
            if setting.of_booking_company_specific:
                setting.company_id.of_booking_validation_note = setting.of_booking_validation_note
            else:
                config_param_obj.set_param(
                    "of.website.planning.booking.validation_note", setting.of_booking_validation_note
                )
