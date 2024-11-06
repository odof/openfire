# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

SELECTION_SEARCH_TYPES = [
    ("distance", "Distance (km)"),
    ("duration", "Duration (min)"),
]

SELECTION_SEARCH_MODES = [
    ("oneway", "One way"),
    ("return", "Return"),
    ("round_trip", "Round trip"),
    ("oneway_or_return", "One way or Return"),
    ("oneway_am_return_pm", "One way if morning / Return if afternoon"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    search_mode = fields.Selection(
        string="(OF) Search mode",
        selection=SELECTION_SEARCH_MODES,
        required=True,
        default="oneway_or_return",
        config_parameter="of.planning.tour.search_mode",
    )
    search_type = fields.Selection(
        string="(OF) Search type",
        selection=SELECTION_SEARCH_TYPES,
        required=True,
        default="duration",
        config_parameter="of.planning.tour.search_type",
    )
    planning_default_intervention_template_id = fields.Many2one(
        comodel_name="of.planning.intervention.template",
        string="(OF) Default intervention template for searching",
        help="Default intervention template to use when creating for an appointment.",
        config_parameter="of.planning.tour.default_planning_intervention_template_id",
    )

    # Tour planning
    nbr_days_tour_creation = fields.Integer(
        string="(OF) Tours // Create Tours over __ days",
        default=30,
        required=True,
        help="Defines the number of days on which to create the routes for each employee whose work hours "
        "are defined. Maximum: 180 days.",
        config_parameter="of.planning.tour.nbr_days_tour_creation",
    )
    tour_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="res_config_settings_tour_employee_rel",
        string="(OF) Tours // Employees",
        help="Create tours for these employees only.",
        compute="_compute_tour_employee_ids",
        inverse="_inverse_tour_employee_ids_str",
    )
    tour_employee_ids_str = fields.Char(
        string="Tours employees in String",
        config_parameter="of.planning.tour.tour_employee_ids",
        help="Technical field to store M2M fields into a config parameter. As config_parameters does not accept m2m "
        "field, we store the fields with a comma separated string into a Char config field.",
    )
    tour_day_ids = fields.Many2many(
        comodel_name="of.days",
        relation="res_config_settings_tour_days_rel",
        string="(OF) Tours // Days",
        compute="_compute_tour_day_ids",
        inverse="_inverse_tour_day_ids_str",
        help="Create tours for these days only",
    )
    tour_day_ids_str = fields.Char(
        string="Tours days in String",
        config_parameter="of.planning.tour.tour_day_ids",
        help="Technical field to store M2M fields into a config parameter. As config_parameters does not accept m2m "
        "field, we store the fields with a comma separated string into a Char config field.",
    )
    tour_am_limit_float = fields.Float(
        string="(OF) Tours // Morning/Afternoon break hour",
        config_parameter="of.planning.tour.tour_am_limit_float",
        default=13.0,
        help="Defines the break hour between morning and afternoon. Interventions starting before this hour will be "
        "considered in the morning and vice versa.",
    )
    of_planning_tour_manual_creation = fields.Boolean(
        string="(OF) Manual tour creation authorized",
        help="Allows users to manually create tours.",
    )

    @api.constrains("nbr_days_tour_creation")
    def _check_nbr_days_tour_creation(self):
        for setting in self:
            if setting.nbr_days_tour_creation <= 0 or setting.nbr_days_tour_creation > 180:
                raise ValidationError(
                    _("The number of days for the tours creation must be positive and can't exceed 180."))

    @api.constrains("tour_day_ids")
    def _check_tour_day_ids(self):
        for setting in self:
            if not setting.tour_day_ids:
                raise ValidationError(_("You must select at least one day for the tours creation."))

    @api.depends("tour_day_ids_str")
    def _compute_tour_day_ids(self):
        days_obj = self.env["of.days"]
        for setting in self:
            if setting.tour_day_ids_str:
                ids = setting.tour_day_ids_str.split(",")
                ids = [int(id) for id in ids if id.isdigit()]
                setting.tour_day_ids = days_obj.search([("id", "in", ids)])
            else:
                setting.tour_day_ids = None

    def _inverse_tour_day_ids_str(self):
        for setting in self:
            if setting.tour_day_ids:
                setting.tour_day_ids_str = ",".join(setting.tour_day_ids.mapped(lambda x: str(x.id)))
            else:
                setting.tour_day_ids_str = ""

    @api.depends("tour_employee_ids_str")
    def _compute_tour_employee_ids(self):
        for setting in self:
            if setting.tour_employee_ids_str:
                ids = setting.tour_employee_ids_str.split(",")
                ids = [int(id) for id in ids if id.isdigit()]
                setting.tour_employee_ids = self.env["hr.employee"].search([("id", "in", ids)])
            else:
                setting.tour_employee_ids = None

    def _inverse_tour_employee_ids_str(self):
        for setting in self:
            if setting.tour_employee_ids:
                setting.tour_employee_ids_str = ",".join(setting.tour_employee_ids.mapped(lambda x: str(x.id)))
            else:
                setting.tour_employee_ids_str = ""

    def set_values(self):
        res = super().set_values()
        self._set_of_planning_tour_manual_creation()
        return res

    def get_values(self):
        res = super().get_values()
        of_planning_tour_manual_creation = self.env["ir.config_parameter"].get_param(
            "of.planning.tour.group_of_planning_tour_manual_creation"
        )
        res.update(of_planning_tour_manual_creation=of_planning_tour_manual_creation)
        return res

    def _set_of_planning_tour_manual_creation(self):
        self.ensure_one()
        group_manual_creation = self.env.ref("of_planning_tour.group_of_planning_tour_manual_creation")
        group_no_manual_creation = self.env.ref("of_planning_tour.group_of_planning_tour_no_manual_creation")
        # Get all users except the deactivated ones (e.g SUPERUSER_ID)
        all_users = self.env["res.users"].with_context(active_test=True).search([])
        if self.of_planning_tour_manual_creation:
            group_manual_creation.write({"users": [Command.set(all_users.ids)]})
        else:
            group_no_manual_creation.write({"users": [Command.set(all_users.ids)]})
        self.env["ir.config_parameter"].set_param(
            "of.planning.tour.group_of_planning_tour_manual_creation", int(self.of_planning_tour_manual_creation)
        )
