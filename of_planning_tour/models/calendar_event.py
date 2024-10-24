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
            saved_events_data = {
                event: {
                    "dates": event._get_tour_dates(),
                    "start": event.start,
                    "of_partner_latitude": event.of_partner_latitude,
                    "of_partner_longitude": event.of_partner_longitude,
                    "duration": event.duration,
                    "of_force_dates": event.of_force_dates,
                    "of_state": event.of_state,
                    "of_employee_ids": event.of_employee_ids.ids,
                    "active": event.active,
                }
                for event in self
            }

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
        # Get interventions that have changed their geodata, hours, duration, force_date or date
        # or that have been cancelled, reopened, postponed or have changed their employees assignments, to update tours
        # accordingly
        events_geodata_changed = self._get_events_geodata_updated(saved_events_data)
        events_hours_changed = self._get_events_only_hours_changed(saved_events_data)
        events_duration_changed = self._get_events_duration_changed(saved_events_data)
        events_force_date_changed = self._get_events_force_date_changed(saved_events_data)
        events_start_date_changed = self._get_events_start_date_changed(saved_events_data)
        events_cancelled = self._get_cancelled_events(saved_events_data)
        events_reopened = self._get_reopened_events(saved_events_data)
        events_postponed = self._get_postponed_events(saved_events_data)
        events_employee_changed = self._get_events_employee_changed(saved_events_data)
        events_archived = self._get_archived_events(saved_events_data)
        events_unarchived = self._get_unarchived_events(saved_events_data)

        # Build dictionaries of interventions to move, remove with their dates before the update
        events_to_move = {
            event: saved_events_data[event]["dates"]
            for event in events_duration_changed
            | events_force_date_changed
            | events_start_date_changed
            | events_unarchived
        }
        events_to_remove = {
            event: saved_events_data[event]["dates"]
            for event in events_start_date_changed | events_cancelled | events_postponed | events_archived
            if event not in events_to_move
        }

        all_tours_to_recompute = self.env["of.planning.tour"].search(
            [("date", ">=", datetime.now().date()), ("date", "in", all_dates), ("employee_id", "in", all_employees.ids)]
        )

        # Updates tours data based on the changes in interventions
        events_to_move and self.action_update_tour_lines(events_to_move)
        events_to_remove and self.action_remove_from_tour(events_to_remove)
        events_hours_changed and self.action_reorder_tours(events_hours_changed)
        events_geodata_changed and self.action_resync_and_update_tours(events_geodata_changed)
        events_to_transfert and self.action_transfert_events_between_tours(events_to_transfert)
        events_reopened and self.action_create_tours()

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

    def _get_archived_events(self, saved_vals):
        """
        Filters and returns the events that have been archived.
        """

        return self.filtered(lambda ev: ev in saved_vals and saved_vals[ev]["active"] is True and ev.active is False)

    def _get_unarchived_events(self, saved_vals):
        """
        Filters and returns the events that have been unarchived.
        """
        return self.filtered(lambda ev: ev in saved_vals and saved_vals[ev]["active"] is False and ev.active is True)

    @api.model
    def _get_fields_trigger_tour_compute(self):
        """
        Returns a list of fields that trigger the tour computation.
        """
        return ["start", "of_employee_ids", "of_state", "duration", "of_address_id", "of_force_dates", "active"]

    def _get_events_geodata_updated(self, saved_vals):
        """
        Filters and returns the events whose dates have been changed.
        """

        def _compare_geodata(ev, vals):
            if ev not in vals:
                return False

            event_vals = vals[ev]
            address_id = ev.of_address_id and ev.of_address_id.id or False
            if "of_partner_latitude" in event_vals and ev.of_partner_latitude != event_vals.get("of_partner_latitude"):
                return True
            if "of_partner_longitude" in event_vals and ev.of_partner_longitude != event_vals.get(
                "of_partner_longitude"
            ):
                return True
            return "of_address_id" in event_vals and address_id != event_vals.get("of_address_id")

        return self.filtered(lambda ev: _compare_geodata(ev, saved_vals))

    def _get_events_start_date_changed(self, saved_vals):
        """
        Filters and returns the events whose start date have been changed.
        """

        def _compare_dates(ev, vals):
            if ev not in vals or "start" not in vals[ev]:
                return False
            date_saved = fields.Datetime.from_string(vals[ev]["start"])
            return ev.start != date_saved and ev.start.date() != date_saved.date()

        return self.filtered(lambda ev: _compare_dates(ev, saved_vals))

    def _get_cancelled_events(self, saved_vals):
        """
        Filters and returns the events that have been cancelled.
        """
        return self.filtered(
            lambda ev: ev in saved_vals and saved_vals[ev]["of_state"] != "cancel" and ev.of_state == "cancel"
        )

    def _get_reopened_events(self, saved_vals):
        """
        Filters and returns the events that have been reopened (from cancelled or postponed to another state).
        """
        return self.filtered(
            lambda ev: ev in saved_vals
            and saved_vals[ev]["of_state"] in ["cancel", "postponed"]
            and ev.of_state != "cancel"
        )

    def _get_postponed_events(self, saved_vals):
        """
        Filters and returns the events that have been postponed.
        """
        return self.filtered(
            lambda ev: ev in saved_vals and saved_vals[ev]["of_state"] != "postponed" and ev.of_state == "postponed"
        )

    def _get_events_only_hours_changed(self, saved_vals):
        """
        Filters and returns the events whose hours have been changed. If the start date has been changed,
        it will not be considered as a change in hours and will fallback to the `_get_events_start_date_changed` method.
        """

        def _compare_hours(ev, vals):
            if ev not in vals or "start" not in vals[ev]:
                return False
            date_saved = fields.Datetime.from_string(vals[ev]["start"])
            if date_saved.date() != ev.start.date():
                return False
            return (
                ev.start.hour != date_saved.hour
                or ev.start.minute != date_saved.minute
                or ev.start.second != date_saved.second
            )

        return self.filtered(lambda ev: _compare_hours(ev, saved_vals))

    def _get_events_duration_changed(self, saved_vals):
        """
        Filters and returns the events whose duration has been changed.
        """
        return self.filtered(
            lambda ev: ev in saved_vals
            and saved_vals[ev].get("duration")
            and ev.duration != saved_vals[ev].get("duration")
        )

    def _get_events_force_date_changed(self, saved_vals):
        """
        Filters and returns the events whose `of_force_dates` field has been changed.
        """
        return self.filtered(
            lambda ev: ev in saved_vals
            and "of_force_dates" in saved_vals[ev]
            and ev.of_force_dates != saved_vals[ev].get("of_force_dates")
        )

    def _get_events_employee_changed(self, saved_vals):
        """
        Filters and returns the events whose employees have been changed.
        """
        return self.filtered(
            lambda ev: ev in saved_vals
            and "of_employee_ids" in saved_vals[ev]
            and ev.of_employee_ids.ids != saved_vals[ev].get("of_employee_ids")
        )

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
