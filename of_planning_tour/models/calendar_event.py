# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    of_state = fields.Selection(selection_add=[("being_optimized", "Being optimized")])
    of_tour_ids = fields.Many2many(
        comodel_name="of.planning.tour",
        relation="calendar_event_of_planning_tour_rel",
        column1="event_id",
        column2="tour_id",
        compute="_compute_of_tour_ids",
        store=True,
        string="Tours",
    )
    of_tour_number = fields.Char(compute="_compute_tour_data", string="Tour number")
    of_partner_latitude = fields.Float(related="of_address_id.partner_latitude", string="Latitude")
    of_partner_longitude = fields.Float(related="of_address_id.partner_longitude", string="Longitude")

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("start", "stop", "of_employee_ids", "of_task_id")
    def _compute_of_has_conflict_warning(self):
        if self.env.context.get("of_avoid_tour_process"):
            for event in self:
                event.of_has_conflict_warning = False
        else:
            super()._compute_of_has_conflict_warning()

    @api.depends("of_employee_ids", "start", "of_tour_ids.date", "of_tour_ids.employee_id", "of_state")
    def _compute_of_tour_ids(self):
        tour_obj = self.env["of.planning.tour"]
        state_values_to_exclude = tour_obj._get_intervention_state_values_to_exclude()
        for event in self:
            if event.of_employee_ids and event.start and event.of_state not in state_values_to_exclude:
                tours = tour_obj.search(
                    [("employee_id", "in", event.of_employee_ids.ids), ("date", "=", event.start_date)]
                )
                event.of_tour_ids = [Command.clear()] + [Command.link(tour.id) for tour in tours]

    def _compute_tour_data(self):
        if self.env.context.get("of_active_tour_id"):
            tour = self.env["of.planning.tour"].browse(self.env.context.get("of_active_tour_id"))

            # Get all interventions of the tour
            events_by_address_dict = {}
            tour_events = self.search(
                [
                    ("of_employee_ids", "in", tour.employee_id.id),
                    ("start", "<=", tour.date),
                    ("stop", ">=", tour.date),
                    ("of_state", "not in", tour._get_intervention_state_values_to_exclude()),
                    ("of_type", "=", "intervention"),
                ],
                order="start",
            )
            # Get all interventions of the tour by address
            for idx, event in enumerate(tour_events, 1):
                if not events_by_address_dict.get(event.of_address_id.id):
                    events_by_address_dict[event.of_address_id.id] = {event: idx}
                else:
                    events_by_address_dict[event.of_address_id.id][event] = idx

            # Compute the color and the number in the tour for each intervention
            for event in self:
                events_at_address = events_by_address_dict.get(event.of_address_id.id)
                tour_number = ", ".join(map(str, events_at_address.values())) if events_at_address else False
                event.of_tour_number = tour_number
        else:
            for event in self:
                event.of_tour_number = False

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        # allows to force creation of tours without triggering the tour creation process in some cases (e.g unit tests)
        if not self.env.context.get("of_avoid_tour_process") or self.env.context.get("of_force_tour_creation"):
            events.action_create_tours()
        return events

    def write(self, vals):
        fields_trigger_tour_compute = self._get_fields_trigger_tour_compute()
        if not self.env.context.get("of_avoid_tour_process") and any(
            field_name in vals for field_name in fields_trigger_tour_compute
        ):
            previous_tours = self.filtered(lambda rec: isinstance(rec.id, int)).mapped("of_tour_ids")

        res = super().write(vals)

        # Update tours based on the changes in interventions
        if not self.env.context.get("of_avoid_tour_process") and any(
            field_name in vals for field_name in fields_trigger_tour_compute
        ):
            self.filtered(lambda rec: isinstance(rec.id, int))._handle_tour_update(previous_tours)
        return res

    def name_get(self):
        if not self.env.context.get("of_from_tour"):
            return super().name_get()

        return [
            (event.id, f"{event.of_type_id.name or event.name} - {event.of_address_id.name or 'N/A'}") for event in self
        ]

    def unlink(self):
        if not self.env.context.get("of_avoid_tour_process"):
            tours = self._events_unlink_get_tours_to_recompute()

        result = super().unlink()

        if not self.env.context.get("of_avoid_tour_process") and tours:
            # As we are deleting a tour line, we need to recompute sequences and OSRM data
            tours._reset_sequence()
            tours._osrm_recompute_data_if_needed(force=True)
            tours._reorganize_available_slot()
        return result

    # --------------------------------------------------------------------------
    # Actions methods
    # --------------------------------------------------------------------------

    def action_create_tours(self):
        for event in self:
            tours = event._create_tour()
            self.env.add_to_compute(event._fields["of_tour_ids"], event)
            tours.action_update_lines_data()

    def action_button_open_tour_appointment_wizard(self):
        """
        Open the tour appointment wizard to plan an intervention.

        This method is triggered when the user clicks on a button to open the tour appointment wizard.
        It checks if the address is geocoded and raises an error if it is not.
        It then creates a new tour appointment wizard with default values and computes the time slots.
        Finally, it returns an action to open the tour appointment wizard form view.

        Returns:
            dict: action to open the tour appointment wizard form view

        Raises:
            UserError: if the address is not geocoded
        """
        self.ensure_one()
        if self.of_has_geolocalize_warning:
            raise UserError(_("This address is not geocoded, please geocode it to plan an intervention."))

        tour_appointment_obj = self.env["of.tour.appointment.wizard"]
        icp_obj = self.env["ir.config_parameter"]
        context = self.env.context.copy()

        default_planning_intervention_template = icp_obj.sudo().get_param(
            "of.planning.tour.default_planning_intervention_template_id"
        )

        default_values = tour_appointment_obj.with_context(
            active_model=self._name,
            active_ids=self.ids,
        ).default_get(tour_appointment_obj._fields.keys())

        default_values.update(
            {
                "request_id": self.of_request_id.id,
                "company_id": self.of_company_id.id,
                "partner_id": self.of_partner_id.id,
                "template_id": self.of_template_id.id or int(default_planning_intervention_template),
            }
        )

        tour_appointment_wizard = tour_appointment_obj.create(default_values)
        # start time slots computing
        tour_appointment_wizard._populate_line_ids()
        form_view_id = self.env.ref("of_planning_tour.of_tour_appointment_wizard_view_form").id
        return {
            "name": _("Plan again"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "of.tour.appointment.wizard",
            "views": [(form_view_id, "form")],
            "res_id": tour_appointment_wizard.id,
            "target": "current",
            "context": context,
        }

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _handle_tour_update(self, previous_tours):
        """
        Handles the update of tours for calendar events.

        This method performs various actions based on the changes in the calendar event data.
        It updates tour lines, reorders tours, and resyncs and updates tours based on the changes in interventions.
        It also transfers events between tours based on the changes in employee assignments.

        Args:
            previous_tours (recordset): The event tours before the update.
        Returns:
            None
        """
        old_dates = previous_tours.mapped("date")
        new_dates = self.mapped("start_date")
        all_dates = list(set(old_dates + new_dates))

        old_employees = previous_tours.mapped("employee_id")
        new_employees = self.mapped("of_employee_ids")
        all_employees = old_employees + new_employees

        all_tours_to_recompute = self.env["of.planning.tour"].search(
            [("date", ">=", datetime.now().date()), ("date", "in", all_dates), ("employee_id", "in", all_employees.ids)]
        )

        for event in self:
            all_tours_to_recompute |= event._create_tour()

        for tour in all_tours_to_recompute.sudo():
            # Add potential new lines
            tour._populate_tour_lines()
            # Remove potential old lines
            tour._remove_tour_lines()
            # Reorder lines
            tour._reset_sequence()
            # Recompute geo data
            for line in tour.tour_line_ids.sorted("date_start"):
                line._update_line_data_from_intervention()
                line._compute_line_data()
                line._osrm_update_line_data()
                line.intervention_id.of_travel_duration = line.duration_one_way
            # Recompute available slots
            tour._reorganize_available_slot()

    @api.model
    def _get_fields_trigger_tour_compute(self):
        """
        Returns a list of fields that trigger the tour computation.
        """
        return [
            "start",
            "of_employee_ids",
            "of_state",
            "duration",
            "of_address_id",
            "of_force_dates",
            "of_resource_id",
            "active",
        ]

    def _get_tour_dates(self):
        """
        Returns a list of tour dates between the start_date and stop_date of the calendar event.

        Returns:
            list: A list of tour dates as strings.
        """
        self.ensure_one()

        start_date = self.start_date
        if not self.start_date:
            return []

        end_date = self.stop_date
        res = [start_date]
        if end_date != start_date:  # If the event is split over multiple days
            eval_date = start_date + timedelta(days=1)
            while eval_date <= end_date:
                res.append(eval_date)
                eval_date += timedelta(days=1)

        return [fields.Date.to_string(date) for date in res]

    def _create_tour(self):
        """
        Create tours based on the calendar event.

        This method creates tours for each employee assigned to the calendar event.
        If a tour already exists for a specific date and employee, it updates sectors to include the address sector.

        Returns:
            tours (recordset): The created or updated tours.
        """
        self.ensure_one()

        tour_obj = self.env["of.planning.tour"]
        tours = tour_obj.browse()
        if self.of_state in tour_obj._get_intervention_state_values_to_exclude():
            return tours

        dates_eval = self._get_tour_dates()
        address = self.of_address_id
        return tour_obj._create_tours_for_employees(self.of_employee_ids, dates_eval, address.of_tech_sector_id)

    def _events_unlink_get_tours_to_recompute(self):
        """
        Get tours to recompute based on the deleted events.
        """
        tours_dates = [event._get_tour_dates() for event in self]
        flattened_tours_dates = [item for sublist in tours_dates for item in sublist]
        existing_tour_lines = (
            self.env["of.planning.tour.line"]
            .sudo()
            .search([("intervention_id", "in", self.ids), ("tour_id.date", "in", flattened_tours_dates)])
        )  # Tour lines are deleted in cascade so we need to get them before
        return existing_tour_lines and existing_tour_lines.mapped("tour_id") or self.env["of.planning.tour"].browse()

    @api.model
    def _custom_get_color_map(self):
        return {
            "title": "",
            "values": (
                {"label": _("SR to plan"), "value": "green"},
                {"label": _("Tour Interventions"), "value": "blue"},
            ),
        }
