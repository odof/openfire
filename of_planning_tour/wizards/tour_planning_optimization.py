# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

from ..models.of_planning_tour import DEFAULT_AM_LIMIT_FLOAT
from ..models.of_planning_tour_line import AVAILABLE_COLORS_TOUR_LINES, ROUTES_AVAILABLE_COLORS


class OFPlanningTourOptimizationWizard(models.TransientModel):
    """Wizard to optimize the tour lines."""

    _name = "of.planning.tour.optimization.wizard"
    _inherit = "of.planning.tour.wizard.mixin"

    _description = __doc__

    state = fields.Selection(selection=[("init", "Init"), ("optimized", "Optimized")], default="init")
    optim_mode = fields.Selection(
        selection=[
            ("all", "All day"),
            ("half", "Half day"),
            ("morning", "Morning"),
            ("afternoon", "Afternoon"),
        ],
        string="Optimization mode",
        required=True,
        default="all",
    )

    line_ids = fields.One2many(
        comodel_name="of.planning.tour.optimization.line.wizard", inverse_name="wizard_id", string="Lines to optimize"
    )
    optimized_line_ids = fields.One2many(
        comodel_name="of.planning.tour.optimization.line.wizard",
        compute="_compute_optimized_line_ids",
        string="Optimized lines",
    )
    map_optimized_line_ids = fields.One2many(
        comodel_name="of.planning.tour.optimization.line.wizard",
        compute="_compute_optimized_line_ids",
        string="Optimized lines (map)",
    )
    can_overlap_lunchbreak = fields.Boolean(string="Can overlap lunch break ?")
    display_overlap_opt = fields.Boolean(
        string="Display overlap option ?",
        compute="_compute_display_overlap_opt",
        help="Technical field to display the overlap option in the wizard view when needed",
    )
    display_multi_employees_opt = fields.Boolean(
        string="Display multi employees option ?",
        compute="_compute_display_multi_employees_opt",
        help="Technical field to display the multi employees option in the wizard view when needed",
    )
    total_distance = fields.Float(related="tour_id.total_distance")
    total_duration = fields.Float(related="tour_id.total_duration")
    new_total_distance = fields.Float(
        string="New total dist. (km)",
        readonly=True,
        help="The optimized total distance of the tour, that includes the distance from the start address and "
        "to the stop address (km)",
    )
    new_total_duration = fields.Float(
        string="New total dur. (h)",
        readonly=True,
        help="The optimized total duration of the tour, that includes the duration from the start address and "
        "to the stop address (h)",
    )
    # Compute fields
    start_address_id = fields.Many2one(comodel_name="res.partner", compute="_compute_tour_data")
    return_address_id = fields.Many2one(comodel_name="res.partner", compute="_compute_tour_data")
    map_latitude = fields.Text(compute="_compute_tour_data")
    map_longitude = fields.Text(compute="_compute_tour_data")
    additional_records = fields.Text(compute="_compute_tour_data")
    map_tour_line_ids = fields.One2many(comodel_name="of.planning.tour.line", compute="_compute_tour_data")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("tour_id")
    def _compute_tour_data(self):
        for wizard in self:
            wizard.start_address_id = wizard.tour_id.start_address_id.id or False
            wizard.return_address_id = wizard.tour_id.return_address_id.id or False
            wizard.additional_records = wizard.tour_id.additional_records
            wizard.map_tour_line_ids = wizard.tour_id.map_tour_line_ids.ids or False
            wizard.map_latitude = wizard.tour_id.map_latitude
            wizard.map_longitude = wizard.tour_id.map_longitude

    def _compute_optimized_line_ids(self):
        for wizard in self:
            sorted_lines = wizard.line_ids.sorted("new_index")
            wizard.map_optimized_line_ids = sorted_lines
            wizard.optimized_line_ids = sorted_lines

    def _compute_display_overlap_opt(self):
        """Compute the display_overlap_opt field to display the overlap option in the wizard view when needed.
        This option is displayed when at least one of the tour lines could overlap the lunch break.
        And it's hidden when the user has already checked the option and relaunch the optimization.
        """
        for wizard in self:
            wizard.display_overlap_opt = any(wizard.mapped("map_optimized_line_ids.could_overlap"))

    def _compute_display_multi_employees_opt(self):
        """Compute the display_multi_employees_opt field to display the multi employees option in the wizard view
        when needed.
        This option is displayed when at least one of the tour lines has got multiple employees.
        It will allow the user to choose if he wants to force the new date on interventions with multiple employees.
        """
        for wizard in self:
            tour_lines = wizard.mapped("map_optimized_line_ids.tour_line_id")
            wizard.display_multi_employees_opt = any(len(line.employee_ids) > 1 for line in tour_lines)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_button_optimize(self):
        """Optimize the tour lines.

        :return: the action to open the wizard
        :rtype: dict
        """
        self.ensure_one()
        self.tour_id._osrm_test_connection()
        self.action_optimize()
        self.state = "optimized"
        return self.action_button_open(custom_title=self.tour_id.name)

    def action_button_relaunch(self):
        return self.action_button_optimize()

    def action_button_preview_overlap_lb(self):
        """Preview optimized tour lines with the lunch break overlap option checked.
        This option is used to allow tour lines to overlap the lunch break time slot.
        """
        self.ensure_one()
        self.can_overlap_lunchbreak = True
        return self.action_button_optimize()

    def action_button_validate_overlap_lb(self):
        """Validate optimized tour lines directly after allowing tour lines to overlap the lunch break time slot."""
        self.ensure_one()
        self.can_overlap_lunchbreak = True
        return self.action_button_validate()

    def action_optimize(self):
        """Optimize the tour lines.
        1 - Get the tour lines coordinates and their hints to be able to retrieve them during the process
        2 - Send the request to the OSRM server to get the optimized tour lines with the TSP algorithm
        3 - Update the wizard lines with the new time slot built from the new optimized trip
        4 - Update the wizard lines with the new distance from the new optimized trip
            > We can't get the new distance from the "trip OSRM API", because the trip service response doesn't return
                the distance between each reordered waypoints.
            > We have to compute it manually using the "route OSRM API" with the new optimized route.
        """
        self.ensure_one()

        # build a mapping between tour lines and wizard lines to be able to retrieve them during the process
        wizard_line_mapping = dict(zip(self.mapped("line_ids.tour_line_id"), self.line_ids))

        # get coordinates of the tour lines to optimize to send them to the OSRM server
        # and also get the tour lines data by hint to be able to retrieve them during the process
        if self.optim_mode != "half":
            ordered_waypoints = self._get_optimized_waypoints(self.tour_id, self.optim_mode)
        else:
            waypoints_morning = self._get_optimized_waypoints(self.tour_id, "morning")
            waypoints_morning.pop()

            afternoon_start_address = waypoints_morning[-1]["origin_line_id"].intervention_id.of_address_id

            waypoints_afternoon = self._get_optimized_waypoints(
                self.tour_id, "afternoon", afternoon_start_address=afternoon_start_address
            )
            waypoints_afternoon.pop(0)
            morning_pts_num = len(waypoints_morning)
            for waypoint in waypoints_afternoon:
                waypoint["waypoint_index"] = waypoint["waypoint_index"] + morning_pts_num - 1

            ordered_waypoints = waypoints_morning + waypoints_afternoon

        am_limit_float = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of.planning.tour.tour_am_limit_float", DEFAULT_AM_LIMIT_FLOAT)
        )
        compare_precision = 5

        optimized_lines = self.env["of.planning.tour.line"]

        if self.optim_mode == "afternoon":
            optimized_lines |= self.tour_id.tour_line_ids.filtered(
                lambda tl: float_compare(
                    self.tour_id._get_float_intervention_start_hour(tl.intervention_id),
                    am_limit_float,
                    compare_precision,
                )
                < 0
            )

        for waypoint in ordered_waypoints:
            if waypoint["origin_line_id"]:
                optimized_lines += waypoint["origin_line_id"]

        if self.optim_mode == "morning":
            optimized_lines |= self.tour_id.tour_line_ids.filtered(
                lambda tl: float_compare(
                    self.tour_id._get_float_intervention_start_hour(tl.intervention_id),
                    am_limit_float,
                    compare_precision,
                )
                >= 0
            )

        # update the wizard lines with the new time slot created by the optimization
        self._update_optimization_lines_time_slots(optimized_lines, wizard_line_mapping)

        # as we have modified the order of the interventions, we need to update the wizard lines with
        # the new distance and duration between each interventions
        self._update_totals_and_lines_with_osrm_data(optimized_lines, wizard_line_mapping, update_totals=True)

    def action_button_reset(self):
        """Reset the wizard to its initial state.

        Returns:
            dict: the action to open the wizard
        """
        self.ensure_one()
        self.line_ids.unlink()
        lines_values = [
            Command.create(tour_line._prepare_optimization_line_values()) for tour_line in self.tour_id.tour_line_ids
        ]
        self.write({"state": "init", "line_ids": lines_values, "can_overlap_lunchbreak": False})
        return self.action_button_open(custom_title=self.tour_id.name)

    def action_button_validate(self):
        """Validate the optimized tour.
        Update all the interventions in the lines with the start date got from the optimization.
        Also updates the interventions sequences in the tour and the tour lines's geojson data.

        As we have modified the interventions order, we need to update the tour lines with the new
        distance, duration and time slot between each interventions.

        Returns:
            dict: the action to close the wizard and reload the tour
        """
        self.ensure_one()
        if self.can_overlap_lunchbreak and self.display_overlap_opt:
            # if the user has checked the "can overlap lunchbreak" checkbox and didn't relaunch the optimization,
            # we need to relaunch the optimization to take into account the new lunchbreaks
            self.action_optimize()

        # update the interventions with a temporary state to allow the start date update
        current_events_states = {event: event.of_state for event in self.mapped("line_ids.intervention_id")}
        self.mapped("line_ids.intervention_id").with_context(of_avoid_tour_process=True).write(
            {"of_state": "being_optimized"}
        )
        with self.env.norecompute():  # disable recomputing the fields during the update
            for line in self.line_ids:
                date_before_modification = line.intervention_id.start
                date_deadline_before_modification = line.intervention_id.stop
                force_date_before_modification = line.intervention_id.of_force_dates
                # update the interventions with the new start date
                line.intervention_id.with_context(of_avoid_tour_process=True).write(
                    self._get_new_values_for_intervention(line)
                )
                # update the line with the new sequence and the geojson data updated from the optimization
                tour_line_values = self.tour_id._prepare_tour_line_values(int(line.new_index), line.intervention_id)
                del tour_line_values["tour_id"]
                tour_line_values.update(
                    {
                        "last_modification_date": fields.Datetime.now(),
                        "date_before_modification": date_before_modification,
                        "date_deadline_before_modification": date_deadline_before_modification,
                        "force_date_before_modification": force_date_before_modification,
                        "geometry_data": line.geometry_data,
                        "endpoint_geometry_data": line.endpoint_geometry_data,
                        "endpoint_duration": line.endpoint_duration,
                        "endpoint_distance": line.endpoint_distance,
                        "duration_one_way": line.new_duration,
                        "distance_one_way": line.new_distance,
                        "osrm_query": line.osrm_query,
                    }
                )
                line.tour_line_id.write(tour_line_values)

        self.tour_id.flush_recordset()
        self.tour_id.write({"is_optimized": True, "ignore_alert_optimization_update": False})

        # update the interventions to bring them back to their old states
        for event, state in current_events_states.items():
            event.with_context(of_avoid_tour_process=True).write({"of_state": state})
        return self.action_close_and_reload_tour()

    def action_button_open(self, custom_title=None):
        """Open the wizard view.
        Args:
            custom_title (str): the custom title to add to the wizard title

        Returns:
            dict: the action to open the wizard
        """
        self.ensure_one()
        form_view = self.env.ref("of_planning_tour.of_tour_planning_optimization_wizard_view_form")
        title = _("Optimize tour")
        if custom_title:
            title += f" - {custom_title}"
        return self.action_open_form_view(title, form_view)

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _update_optimization_lines_time_slots(self, optimized_lines, wizard_line_mapping):
        """Update the wizard lines with the new values got from the optimized lines."""
        self.ensure_one()

        # Get the new values for the wizard lines from the optimized tour lines
        values_by_lines = self._get_new_slots_data_by_lines(optimized_lines, wizard_line_mapping, time_slot_label=True)
        # Update the wizard lines with the computed values
        for wizard_line, new_values in values_by_lines.items():
            wizard_line.write(new_values)

    @api.model
    def _get_optimized_waypoints(self, tour, mode, afternoon_start_address=False):
        coordinates = tour._osrm_get_tour_coordinates_data(mode, afternoon_start_address=afternoon_start_address)

        # send the request to the OSRM server to get the optimized tour lines with the TSP algorithm
        res = tour._osrm_send_trip_request(coordinates_str=";".join(coord["coord_str"] for coord in coordinates))

        if res.get("code") != "Ok":
            raise UserError(_("Error during the optimization process: %(error)s", error=res.get("message")))

        waypoints = res.get("waypoints")

        if not waypoints:
            # we should always get a list of waypoints here
            raise UserError(_("No optimized tour lines found."))

        for index, waypoint in enumerate(waypoints):
            waypoint["origin_line_id"] = coordinates[index]["origin_line_id"]

        # sort the waypoints by index to get the optimized tour lines in the right order
        # OSRM will always return the data in the input order, so we need to sort them by index
        waypoints = sorted(waypoints, key=lambda k: k["waypoint_index"])

        return waypoints


class OFPlanningTourOptimizationLineWizard(models.TransientModel):
    """Wizard line to optimize the tour lines."""

    _name = "of.planning.tour.optimization.line.wizard"
    _inherit = "of.planning.tour.wizard.line.mixin"

    _description = __doc__

    wizard_id = fields.Many2one(comodel_name="of.planning.tour.optimization.wizard", string="Wizard")
    wizard_state = fields.Selection(string="State", related="wizard_id.state")
    new_intervention_id = fields.Many2one(
        comodel_name="calendar.event",
        string="New Intervention",
        help="Technical field used by the map of the optimized tour lines to display data on the map",
    )
    is_flexible = fields.Boolean(string="Flexible", related="intervention_id.of_is_flexible")
    employee_ids = fields.Many2many(related="intervention_id.of_employee_ids", string="Employees", readonly=True)
    old_index = fields.Char(string="Old index")
    old_time_slot = fields.Char()
    new_index = fields.Char(string="New index")
    new_time_slot = fields.Char()
    old_duration = fields.Float(string="Old Duration (h)")
    old_distance = fields.Float(string="Old Distance (km)")
    # Map fields
    geo_lat = fields.Float(related="new_intervention_id.of_partner_latitude", string="Latitude", readonly=True)
    geo_lng = fields.Float(related="new_intervention_id.of_partner_longitude", string="Longitude", readonly=True)
    duration = fields.Float(related="new_intervention_id.duration", string="Duration", readonly=True)
    task_name = fields.Char(related="new_intervention_id.of_task_id.name", readonly=True, string="Task")
    partner_name = fields.Char(related="new_intervention_id.of_partner_id.name", readonly=True, string="Partner")
    address_zip = fields.Char(related="new_intervention_id.of_address_id.zip", readonly=True)
    address_city = fields.Char(related="new_intervention_id.of_address_city", readonly=True)
    partner_phone = fields.Char(related="new_intervention_id.of_partner_id.phone", readonly=True)
    partner_mobile = fields.Char(related="new_intervention_id.of_partner_id.mobile", readonly=True)
    tour_number = fields.Char(related="new_index", string="Tour number", readonly=True)
    hexa_color = fields.Char(string="Hexa color", compute="_compute_hexa_color")
    date_start = fields.Datetime(related="new_intervention_id.start", string="Start date", readonly=True)
    date_stop = fields.Datetime(related="new_intervention_id.stop", string="End date", readonly=True)
    map_latitude = fields.Text(related="wizard_id.map_latitude")
    map_longitude = fields.Text(related="wizard_id.map_longitude")
    is_first_line_of_tour = fields.Boolean()
    is_last_line_of_tour = fields.Boolean()

    @api.depends("intervention_id")
    def _compute_hexa_color(self):
        tours = self.mapped("wizard_id.tour_id")
        color_padding_by_tour = {
            tour: max(len(ROUTES_AVAILABLE_COLORS) // len(tour.tour_line_ids), 1) for tour in tours
        }
        last_index = 0
        for line in self.sorted(key=lambda line: int(line.new_index)):
            color_padding = color_padding_by_tour[line.wizard_id.tour_id]
            sequence = int(line.new_index) - 1 if int(line.new_index) > 0 else 0
            color_index = last_index + color_padding if sequence > 0 else last_index
            last_index = color_index
            line.hexa_color = AVAILABLE_COLORS_TOUR_LINES[min(color_index, len(AVAILABLE_COLORS_TOUR_LINES) - 1)]
