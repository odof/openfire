# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import json

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

from odoo.addons.of_utils.models.misc import float_2_hours_minutes

from ..models.of_planning_tour import TZ_EUROPE_PARIS


class OFPlanningTourWizardMixin(models.AbstractModel):
    """Mixin class for the Tour Planning Wizard"""

    _name = "of.planning.tour.wizard.mixin"
    _description = __doc__

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if (
            not self.env.context.get("default_tour_id")
            and self.env.context.get("active_model") == "of.planning.tour"
            and self.env.context.get("active_id")
        ):
            res["tour_id"] = self.env.context.get("active_id")
        return res

    tour_id = fields.Many2one(comodel_name="of.planning.tour", string="Tour", required=True, ondelete="cascade")
    name = fields.Char(compute="_compute_tour_name")

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    def _compute_tour_name(self):
        for wizard in self:
            wizard.name = (
                _("Tour optimization") if hasattr(wizard, "action_button_optimize") else _("Tour reorganization")
            )

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------

    def action_close_and_reload_tour(self):
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_open_form_view(self, title, form_view):
        self.ensure_one()
        context = self.env.context.copy()
        return {
            "name": title,
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "view_id": form_view.id,
            "res_id": self.id,
            "domain": [],
            "target": "new",
            "context": context,
        }

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def _update_totals_and_lines_with_osrm_data(self, ordered_lines, wizard_line_mapping, update_totals=False):
        """Updates wizard lines with the new OSRM data depending on the ordered lines.
        If update_totals is True, the total distance and duration of the wizard will be updated.

        Args:
            ordered_lines (of.planning.tour.line): list of tour lines ordered by the optimization or the user
            wizard_line_mapping (dict): mapping between tour lines and wizard lines
            update_totals (bool): boolean to indicate if the total distance and duration of the wizard should be updated

        Returns:
            None
        """
        self.ensure_one()
        new_total_distance = new_total_duration = 0
        osrm_base_url = self.tour_id._osrm_get_base_url()
        len_optimized_line_order = len(ordered_lines)

        for index, ordered_line in enumerate(ordered_lines):
            geometry_data = endpoint_geometry_data = False
            endpoint_distance = endpoint_duration = distance = duration = 0

            # Get the previous coordinates
            previous_geo_lng = (
                ordered_lines[index - 1].intervention_id.of_partner_longitude
                if index > 0
                else self.tour_id.start_address_id.partner_longitude
            )
            previous_geo_lat = (
                ordered_lines[index - 1].intervention_id.of_partner_latitude
                if index > 0
                else self.tour_id.start_address_id.partner_latitude
            )

            # Get the coordinates of the current intervention
            geo_lng = ordered_line.intervention_id.of_partner_longitude
            geo_lat = ordered_line.intervention_id.of_partner_latitude

            # Build the query string with the previous and current coordinates
            coords_str = f"{previous_geo_lng},{previous_geo_lat};{geo_lng},{geo_lat}"  # noqa
            full_query = f"{osrm_base_url}/{coords_str}?geometries=geojson&steps=true&overview=false"

            # Get the OSRM data steps, distance and duration
            steps, distance, duration = ordered_line._osrm_get_steps_data(full_query)
            geometry_data = [step["geometry"] for step in steps]
            new_total_distance += distance
            new_total_duration += duration

            # If we are on the last line, we have to add distance and duration (to go back to the return address) to
            # the total distance and duration
            if index == len_optimized_line_order - 1:
                coords_str = (
                    f"{geo_lng},{geo_lat};{self.tour_id.return_address_id.partner_longitude}"  # noqa
                    f",{self.tour_id.return_address_id.partner_latitude}"  # noqa
                )
                endpoint_full_query = f"{osrm_base_url}/{coords_str}?geometries=geojson&steps=true&overview=false"
                endpoint_steps, endpoint_distance, endpoint_duration = ordered_line._osrm_get_steps_data(
                    endpoint_full_query
                )
                endpoint_geometry_data = [step["geometry"] for step in endpoint_steps]
                new_total_distance += endpoint_distance
                new_total_duration += endpoint_duration

            geometry_data = geometry_data and json.dumps(geometry_data)
            endpoint_geometry_data = endpoint_geometry_data and json.dumps(endpoint_geometry_data)
            # Update the tour line with the new distance and geojson data
            wizard_line_mapping[ordered_line].write(
                {
                    "new_distance": distance,
                    "new_duration": duration,
                    "geometry_data": geometry_data,
                    "endpoint_geometry_data": endpoint_geometry_data,
                    "endpoint_distance": endpoint_distance,
                    "endpoint_duration": endpoint_duration,
                    "osrm_query": full_query,
                }
            )
        if update_totals:
            # Update the wizard the new total distance and duration
            self.write(
                {
                    "new_total_distance": new_total_distance,
                    "new_total_duration": new_total_duration,
                }
            )

    def _get_new_slots_data_by_lines(self, ordered_lines, wizard_line_mapping, time_slot_label=False):
        """Return a dict with the new slot data by line.
        We are using the ordered lines to rebuild the timeline of the day and guess the new start date
        of an intervention.

        The timeline of the day is rebuild from ordered lines depending on employee's work hours and the
        current start date of the 1st intervention of the morning/the afternoon.

        For exemple the tour was planned with the following lines:
            AM = I1 (08H30 - 09H30), I2 (09H30 - 10H30), I3 (10H30 - 12H00)
            PM = I4 (14H30 - 16H30), I5 (16H30 - 17H00)

        The new planification get from the OSRM TSP is: I3, I2, I1, I5, I4.
        I3 is now the first morning intervention and I5 is now the first afternoon intervention.
        So they should start on the same time as the previous first the morning/afternoon interventions (I1 and I4).

        We also have to take into account the employee's work hours and the disruption of the work hours.
        For exemple if the employee's work hours are 8H30 - 12H30 and 13H30 - 17H00 and the work hours are already
        disrupted by an intervention planned on 11H30 - 13H45, just as below:
            AM = I1 (08H30 - 09H30), I2 (09H30 - 10H30), I3 (10H30 - 11H30), I4 (11H30 - 13H15)
            PM = I5 (13H45 - 15H15), I6 (15H15 - 16H30)
        And the new planification get from the optimization is: I5, I1, I4, I3, I2, I6.
        I4 will end at 13H15 (outside of the workings hours), so I5 should start at 13H30 instead
        of right after I4 at 13H15. With that process we are trying to keep a short break (here 15min)
        between the two interventions.

        Args:
            ordered_lines (of.planning.tour.line): list of tour lines ordered by the optimization or the user
            wizard_line_mapping (dict): dict of tour lines mapped with the wizard lines
            time_slot_label (bool): bool to use as time slot label

        Returns:
            dict: dict of wizard lines updated with the new time slot data
        """
        self.ensure_one()

        # update the tour lines with the optimized tour lines
        employee_hours = (
            self.tour_id._get_employee_working_hours()
        )  # eg: [[8.0, 12.5], [13.5, 17.0]] or [[[8.0, 10.0], [11.0, 12.0]], [[13.0, 18.0]]], etc.
        flattened_employee_hours = [
            item for sublist in employee_hours for item in sublist
        ]  # eg: [[8.0, 10.0], [11.0, 13.0], [13.0, 18.0]]

        # if employee has more than two slots of work hours per day, thats we call it "complex work hours"
        complex_employee_hours = len(employee_hours[0]) > 1 or len(employee_hours[1]) > 1
        start_hour = self.tour_id._get_float_first_tour_hour()  # eg: 8.0
        afternoon_start_hour = self.tour_id._get_tour_afternoon_first_hour_float()  # eg: 13.5
        hours_disrupted, count_wh_disrupted = self.tour_id._is_working_hours_disrupted()  # eg: (False, 0) or (True, 2)

        # allow user to accept that an intervention can ends inside the lunch break time slot (count_wh_disrupted is
        # priority over this option). Reorganization wizard doesn't have this option (yet ?).
        lunchbreak_overlapping = self.can_overlap_lunchbreak if hasattr(self, "can_overlap_lunchbreak") else False
        timeline = []
        result = {}

        len_ordered_lines = len(ordered_lines)
        for index, ordered_line in enumerate(ordered_lines, 1):
            could_overlap = False
            # get the tour line that will be replaced from the current order index
            optz_intervention = ordered_line.intervention_id

            # next available hour for the employee
            new_start_hour = timeline[-1][1] if timeline else start_hour

            # get the max duration of the intervention, case of the "Forced duration"
            duration = (optz_intervention.stop - optz_intervention.start).total_seconds() / 3600.0
            duration = (
                max(optz_intervention.duration, duration)
                if optz_intervention.of_force_dates
                else optz_intervention.duration
            )
            hours, minutes = float_2_hours_minutes(duration)

            # get the new start/end hour for the intervention depending on the employee hours
            if complex_employee_hours:
                len_flattened_employee_hours = len(flattened_employee_hours)
                for i in range(len_flattened_employee_hours):
                    slot_end_hour = flattened_employee_hours[i][1]
                    next_slot_start_hour = (
                        flattened_employee_hours[i + 1][0]
                        if i < len_flattened_employee_hours - 1
                        else flattened_employee_hours[i][1]
                    )
                    if new_start_hour >= slot_end_hour and new_start_hour <= next_slot_start_hour:
                        if count_wh_disrupted <= 0:
                            new_start_hour = next_slot_start_hour
                        else:
                            # we don't want to allow all interventions to be planned outside the working hours
                            # so we subtract the count of disrupted working hours to force the next intervention
                            # to be planned inside the working hours if possible
                            count_wh_disrupted -= 1
                        break
            elif new_start_hour >= employee_hours[0][0][1] and new_start_hour <= employee_hours[1][0][0]:
                if count_wh_disrupted <= 0:
                    new_start_hour = employee_hours[1][0][0]
                else:
                    # same as above, we subtract the count of disrupted working hours
                    count_wh_disrupted -= 1

            new_end_hour = new_start_hour + duration
            if complex_employee_hours:
                for i in range(len_flattened_employee_hours):
                    slot_end_hour = flattened_employee_hours[i][1]
                    next_slot_start_hour = (
                        flattened_employee_hours[i + 1][0]
                        if i < len_flattened_employee_hours - 1
                        else flattened_employee_hours[i][1]
                    )
                    if new_end_hour > slot_end_hour and new_end_hour <= next_slot_start_hour:
                        if count_wh_disrupted <= 0:
                            # we don't want to allow overlapping of interventions if the employee has complex
                            # working hours
                            could_overlap = not complex_employee_hours
                            # We want to start the afternoon tour at the same hour as before the optimization process
                            new_start_hour = max(next_slot_start_hour, afternoon_start_hour)
                            new_end_hour = new_start_hour + duration
                        else:
                            # we don't want to allow all interventions to be planned outside the working hours
                            # so we subtract the count of disrupted working hours to force the next intervention
                            # to be planned inside the working hours if possible
                            count_wh_disrupted -= 1
                        break
            elif not lunchbreak_overlapping and (  # user wants to keep lunchbreak pause if possible
                new_end_hour > employee_hours[0][0][1] and new_end_hour <= employee_hours[1][0][0]
            ):
                if count_wh_disrupted <= 0:
                    could_overlap = True
                    # We want to start the afternoon tour at the same hour as before the optimization process
                    new_start_hour = max(employee_hours[1][0][0], afternoon_start_hour)
                    new_end_hour = new_start_hour + duration
                else:  # same as above, we subtract the count of disrupted working hours
                    count_wh_disrupted -= 1

            # get a datetime object for the new start/end hour. Combine the date and the time to get a datetime object
            # with empty time (00:00:00) and add the new start hour to get the new start datetime
            new_start_datetime = datetime.datetime.combine(
                optz_intervention.start, datetime.time()
            ) + datetime.timedelta(
                hours=new_start_hour
            )  # Not an UTC datetime anymore cause we dropped hours
            new_end_datetime = new_start_datetime + relativedelta(hours=hours, minutes=minutes)

            # get the utc datetime for the new start hour to store it in the database
            new_start_datetime_utc = (
                pytz.timezone(self.env.user.tz or TZ_EUROPE_PARIS)
                .localize(new_start_datetime, is_dst=None)
                .astimezone(pytz.utc)
            )

            # fill the timeline
            timeline.append([new_start_hour, new_end_hour])

            # update the tour line with the new time slot created by the optimization
            result[wizard_line_mapping[ordered_line]] = {
                "could_overlap": could_overlap,
                "avoid_check_overlap": hours_disrupted and count_wh_disrupted == 0,
                "new_index": index,
                "new_date_start": new_start_datetime_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "new_intervention_id": optz_intervention.id,
                "is_first_line_of_tour": index == 1,
                "is_last_line_of_tour": index == len_ordered_lines,
            }
            if time_slot_label:
                # build the new time slot label
                new_start_hour = new_start_datetime.strftime("%H:%M")
                new_end_hour = new_end_datetime.strftime("%H:%M")
                new_time_slot = ordered_line._get_time_slot_intervention_label(
                    force_start_hour=new_start_hour, force_end_hour=new_end_hour
                )
                result[wizard_line_mapping[ordered_line]]["new_time_slot"] = new_time_slot
        return result

    def _get_new_values_for_intervention(self, line):
        """Get the new values for intervention of the optimized/reorganized tour line.
        This method can be overridden to add new values to the intervention during the optimization/reorganization
        process.

        Args:
            line (of.planning.tour.line): the tour line to get the new values for the intervention

        Returns:
            dict: the new values for the intervention
        """
        event_values = {"start": line.new_date_start}
        if not line.could_overlap and line.avoid_check_overlap:
            event_values["of_force_dates"] = True
            hours, minutes = float_2_hours_minutes(line.intervention_id.duration)
            # we need to force the deadline date of the intervention to avoid an empty value for this field
            event_values["stop"] = line.new_date_start + relativedelta(hours=hours, minutes=minutes)
        return event_values


class OFTourPlanningWizardLineMixin(models.AbstractModel):
    "Mixin class for the Tour Planning Line Wizards"
    _name = "of.planning.tour.wizard.line.mixin"
    _description = __doc__

    tour_line_id = fields.Many2one(comodel_name="of.planning.tour.line", string="Tour Line", ondelete="cascade")
    intervention_id = fields.Many2one(comodel_name="calendar.event", string="Event", ondelete="cascade")
    could_overlap = fields.Boolean(string="Could overlap", readonly=True)
    avoid_check_overlap = fields.Boolean(string="Avoid overlap check", readonly=True)
    is_multi_employees = fields.Boolean(string="Multi-employees", compute="_compute_is_multi_employees")
    new_distance = fields.Float(string="New Distance (km)")
    new_duration = fields.Float(string="New Duration (h)")
    new_date_start = fields.Datetime(string="New start date", readonly=True)
    osrm_query = fields.Text(
        string="OSRM query",
        help="Technical field used to see the full OSRM query used to get the distance and duration",
    )
    geometry_data = fields.Text(string="Geojson data", help="Technical field used to display the route on the map")
    endpoint_geometry_data = fields.Text(
        string="Geojson data to the endpoint",
        help="Technical field used to display the route to the endpoint on the map",
    )
    endpoint_distance = fields.Float(
        string="Distance to the endpoint (km)", help="Technical field used to get the distance to the endpoint (in km)"
    )
    endpoint_duration = fields.Float(
        string="Duration to the endpoint (hours)",
        help="Technical field used to get the duration to the endpoint (in hours)",
    )

    def _compute_is_multi_employees(self):
        for line in self:
            line.is_multi_employees = len(line.intervention_id.of_employee_ids) > 1
