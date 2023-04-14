# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
import json
import pytz
from dateutil.relativedelta import relativedelta
from odoo import api, models, fields
from odoo.addons.of_utils.models.of_utils import float_2_heures_minutes


class OFTourPlanningWizardMixin(models.AbstractModel):
    _name = 'of.tour.planning.wizard.mixin'
    _description = "Mixin class for the Tour Planning Wizard"

    @api.model
    def default_get(self, fields_list):
        res = super(OFTourPlanningWizardMixin, self).default_get(fields_list)
        if not self._context.get('default_tour_id') and self.env.context.get('active_model') == 'of.planning.tournee' \
                and self.env.context.get('active_id'):
            res['tour_id'] = self.env.context.get('active_id')
        return res

    tour_id = fields.Many2one(comodel_name='of.planning.tournee', string="Tour", required=True, ondelete='cascade')

    @api.multi
    def _update_totals_and_lines_with_osrm_data(self, ordered_lines, wizard_line_mapping, update_totals=False):
        """ Updates wizard lines with the new OSRM data depending on the ordered lines.
            If update_totals is True, the total distance and duration of the wizard will be updated.

            :param ordered_lines: list of tour lines ordered by the optimization or the user
            :param wizard_line_mapping: mapping between tour lines and wizard lines
            :param update_totals: boolean to indicate if the total distance and duration of the wizard should be updated

            :return: None
        """
        self.ensure_one()
        new_total_distance = 0
        new_total_duration = 0
        osrm_base_url = self.tour_id._get_osrm_base_url()
        len_optimized_line_order = len(ordered_lines)
        for index, ordered_line in enumerate(ordered_lines):
            geojson_data = False
            endpoint_geojson_data = False
            endpoint_distance = 0
            endpoint_duration = 0
            distance = 0
            duration = 0
            # Get the previous coordinates
            previous_geo_lng = ordered_lines[index - 1].intervention_id.geo_lng \
                if index > 0 else self.tour_id.start_address_id.geo_lng
            previous_geo_lat = ordered_lines[index - 1].intervention_id.geo_lat \
                if index > 0 else self.tour_id.start_address_id.geo_lat
            # Get the coordinates of the current intervention
            geo_lng = ordered_line.intervention_id.geo_lng
            geo_lat = ordered_line.intervention_id.geo_lat
            # Build the query string with the previous and current coordinates
            coords_str = "%s,%s;%s,%s" % (previous_geo_lng, previous_geo_lat, geo_lng, geo_lat)
            full_query = '%s/%s?geometries=geojson&steps=true&overview=false' % (osrm_base_url, coords_str)
            # Get the OSRM data steps, distance and duration
            steps, distance, duration = ordered_line._get_osrm_steps_data(full_query)
            geojson_data = [step['geometry'] for step in steps]
            new_total_distance += distance
            new_total_duration += duration
            # If we are on the last line, we have to add the distance and duration to go back to the return address to
            # the total distance and duration
            if index == len_optimized_line_order - 1:
                coords_str = "%s,%s;%s,%s" % (
                    geo_lng, geo_lat, self.tour_id.return_address_id.geo_lng, self.tour_id.return_address_id.geo_lat)
                endpoint_full_query = '%s/%s?geometries=geojson&steps=true&overview=false' % (osrm_base_url, coords_str)
                endpoint_steps, endpoint_distance, endpoint_duration = ordered_line._get_osrm_steps_data(
                    endpoint_full_query)
                endpoint_geojson_data = [step['geometry'] for step in endpoint_steps]
                new_total_distance += endpoint_distance
                new_total_duration += endpoint_duration
            geojson_data = geojson_data and json.dumps(geojson_data)
            endpoint_geojson_data = endpoint_geojson_data and json.dumps(endpoint_geojson_data)
            # Update the tour line with the new distance and geojson data
            wizard_line_mapping[ordered_line].write({
                'new_distance': distance,
                'new_duration': duration,
                'geojson_data': geojson_data,
                'endpoint_geojson_data': endpoint_geojson_data,
                'endpoint_distance': endpoint_distance,
                'endpoint_duration': endpoint_duration,
                'osrm_query': full_query,
            })
        if update_totals:
            # Update the wizard the new total distance and duration
            self.write({
                'new_total_distance': new_total_distance,
                'new_total_duration': new_total_duration,
            })

    @api.multi
    def _get_new_slot_data_by_lines(self, ordered_lines, wizard_line_mapping, time_slot_label=False):
        """ Return a dict with the new slot data by line.
        We are using the ordered lines to rebuild the timeline of the day and guess the new start date
        of an intervention.

        The timeline of the day is rebuild from ordered lines depending on employee's work hours and the
        current start date of the 1st intevention of the morning/the afternoon.

        For exemple the tour was planned with the following lines:
            AM = I1 (08H30 - 09H30), I2 (09H30 - 10H30), I3 (10H30 - 12H00)
            PM = I4 (14H30 - 16H30), I5 (16H30 - 17H00)

        The new plannification get from the OSRM TSP is: I3, I2, I1, I5, I4.
        I3 is now the first morning intervention and I5 is now the first afternoon intervention.
        So they should start on the same time as the previous first the morning/afternoon interventions (I1 and I4).

        We also have to take into account the employee's work hours and the disruption of the work hours.
        For exemple if the employee's work hours are 8H30 - 12H30 and 13H30 - 17H00 and the work hours are already
        disrupted by an intervention planned on 11H30 - 13H45, just as below:
            AM = I1 (08H30 - 09H30), I2 (09H30 - 10H30), I3 (10H30 - 11H30), I4 (11H30 - 13H15)
            PM = I5 (13H45 - 15H15), I6 (15H15 - 16H30)
        And the new planification get from the optimizaion is: I5, I1, I4, I3, I2, I6.
        I4 will end at 13H15 (outside of the workings hours), so I5 should start at 13H30 instead
        of right after I4 at 13H15. With that process we are trying to keep a short break (here 15min)
        between the two interventions.

        :param ordered_lines: list of tour lines ordered by the optimization or the user
        :param wizard_line_mapping: dict of tour lines mapped with the wizard lines
        :param time_slot_label: bool to use as time slot label

        :return: dict of wizard lines updated with the new time slot data.
        :rtype: dict
        """
        self.ensure_one()

        # update the tour lines with the optimized tour lines
        employee_hours = self.tour_id._get_employee_hours()  # ie: [[8.0, 12.5], [13.5, 17.0]]
        flattened_employee_hours = [item for sublist in employee_hours for item in sublist]
        # if employee has more than two slots of work hours per day, thats we call it "complex work hours"
        complex_employee_hours = len(employee_hours[0]) > 1
        start_hour = self.tour_id._get_float_first_tour_hour()  # ie: 8.0
        afternoon_start_hour = self.tour_id._get_float_first_afternoon_tour_hour()  # ie: 13.5
        hours_disrupted, count_wh_disrupted = self.tour_id._is_working_hours_disrupted()  # ie: (False, 0) or (True, 2)
        # allow user to accept that an intervention can ends inside the lunch break time slot (count_wh_disrupted is
        # priority over this option). Reorganization wizard doesn't have this option (yet ?).
        lunchbreak_overlapping = self.can_overlap_lunchbreak if hasattr(self, 'can_overlap_lunchbreak') else False
        timeline = []
        result = {}
        for index, ordered_line in enumerate(ordered_lines, 1):
            could_overlap = False
            # get the tour line that will be replaced from the current order index
            new_intervention = ordered_line.intervention_id

            # next available hour for the employee
            new_start_hour = timeline[-1][1] if timeline else start_hour

            # get the max duration of the intervention, case of the "Forced duration"
            dstart = new_intervention.date
            dstop = new_intervention.date_deadline
            duration = (
                fields.Datetime.from_string(dstop) - fields.Datetime.from_string(dstart)).total_seconds() / 3600.0
            duration = max(
                new_intervention.duree, duration) if new_intervention.forcer_dates else new_intervention.duree
            hours, minutes = float_2_heures_minutes(duration)

            # get the new start/end hour for the intervention depending on the employee hours
            if complex_employee_hours:
                len_flattened_employee_hours = len(flattened_employee_hours)
                for i in range(len_flattened_employee_hours):
                    if new_start_hour >= flattened_employee_hours[i][1] and \
                            new_start_hour <= flattened_employee_hours[i + 1][0]:
                        if count_wh_disrupted <= 0:
                            new_start_hour = flattened_employee_hours[i + 1][0]
                        else:
                            # we don't want to allow all interventions to be planned outside the working hours
                            # so we substract the count of disrupted working hours to force the next intervention
                            # to be planned inside the working hours if possible
                            count_wh_disrupted -= 1
                        break
            elif new_start_hour >= employee_hours[0][0][1] and new_start_hour <= employee_hours[1][0][0]:
                if count_wh_disrupted <= 0:
                    new_start_hour = employee_hours[1][0][0]
                else:
                    # same as above, we substract the count of disrupted working hours
                    count_wh_disrupted -= 1

            new_end_hour = new_start_hour + duration
            if complex_employee_hours:
                for i in range(len_flattened_employee_hours):
                    if new_end_hour > flattened_employee_hours[i][1] and \
                            new_end_hour <= flattened_employee_hours[i + 1][0]:
                        if count_wh_disrupted <= 0:
                            # we don't want to allow overlapping of interventions if the employee has complex
                            # working hours
                            could_overlap = not complex_employee_hours
                            # We want to start the afternoon tour at the same hour as before the optimization process
                            new_start_hour = max(flattened_employee_hours[i + 1][0], afternoon_start_hour)
                            new_end_hour = new_start_hour + duration
                        else:
                            # we don't want to allow all interventions to be planned outside the working hours
                            # so we substract the count of disrupted working hours to force the next intervention
                            # to be planned inside the working hours if possible
                            count_wh_disrupted -= 1
                        break
            elif not lunchbreak_overlapping and (  # user wants to keep lunchbreak pause if possible
                    new_end_hour > employee_hours[0][0][1] and new_end_hour <= employee_hours[1][0][0]):
                if count_wh_disrupted <= 0:
                    could_overlap = True
                    # We want to start the afternoon tour at the same hour as before the optimization process
                    new_start_hour = max(employee_hours[1][0][0], afternoon_start_hour)
                    new_end_hour = new_start_hour + duration
                else:  # same as above, we substract the count of disrupted working hours
                    count_wh_disrupted -= 1

            # get a datetime object for the new start/end hour. Combine the date and the time to get a datetime object
            # with empty time (00:00:00) and add the new start hour to get the new start datetime
            new_start_datetime = datetime.datetime.combine(
                datetime.datetime.strptime(new_intervention.date, '%Y-%m-%d %H:%M:%S'), datetime.time()
            ) + datetime.timedelta(hours=new_start_hour)  # Not an UTC datetime anymore cause we droped hours
            new_end_datetime = new_start_datetime + relativedelta(hours=hours, minutes=minutes)

            # get the utc datetime for the new start hour to store it in the database
            new_start_datetime_utc = pytz.timezone(self.env.user.tz or 'Europe/Paris').localize(
                new_start_datetime, is_dst=None).astimezone(pytz.utc)

            # fill the timeline
            timeline.append([new_start_hour, new_end_hour])

            # update the tour line with the new time slot created by the optimization
            result[wizard_line_mapping[ordered_line]] = {
                'could_overlap': could_overlap,
                'avoid_check_overlap': hours_disrupted and count_wh_disrupted == 0,
                'new_index': index,
                'new_date_start': new_start_datetime_utc.strftime('%Y-%m-%d %H:%M:%S'),
                'new_intervention_id': new_intervention.id,
            }
            if time_slot_label:
                # build the new time slot label
                new_start_hour = new_start_datetime.strftime('%H:%M')
                new_end_hour = new_end_datetime.strftime('%H:%M')
                new_time_slot = ordered_line._get_time_slot_intervention_label(
                    force_start_hour=new_start_hour, force_end_hour=new_end_hour)
                result[wizard_line_mapping[ordered_line]]['new_time_slot'] = new_time_slot
        return result

    def _get_new_values_for_intervention(self, line):
        """ Get the new values for intervention of the optimized/reorganized tour line.
        This method can be overridden to add new values to the intervention during the optimization/reorganization
        process.
        """
        intervention_values = {'date': line.new_date_start}
        if len(line.intervention_id.employee_ids) > 1:
            intervention_values['verif_dispo'] = False
        if not line.could_overlap and line.avoid_check_overlap:
            intervention_values['forcer_dates'] = True
            hours, minutes = float_2_heures_minutes(line.intervention_id.duree)
            # we need to force the deadline date of the intervention to avoid an empty value for this field
            intervention_values['date_deadline_forcee'] = fields.Datetime.to_string(
                fields.Datetime.from_string(line.new_date_start) + relativedelta(hours=hours, minutes=minutes))
        if line.intervention_id.date_deadline_forcee:
            # to avoid a constaint error from "check_coherence_date_forcee", we need to recompute the field
            # "date_deadline_forcee" from the new start date
            forced_date_deadline = fields.Datetime.from_string(line.intervention_id.date_deadline_forcee)
            forced_date_deadline = fields.Datetime.from_string(line.new_date_start) + relativedelta(
                hours=line.intervention_id.duree)
            intervention_values['date_deadline_forcee'] = forced_date_deadline
        return intervention_values

    @api.multi
    def action_close_and_reload_tour(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.multi
    def action_open_form_view(self, title, form_view):
        self.ensure_one()
        context = self._context.copy()
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_id': form_view.id,
            'res_id': self.id,
            'domain': [],
            'target': 'new',
            'context': context
        }


class OFTourPlanningWizardLineMixin(models.AbstractModel):
    _name = 'of.tour.planning.wizard.line.mixin'
    _description = "Mixin class for the Tour Planning Line Wizards"

    tour_line_id = fields.Many2one(comodel_name='of.planning.tour.line', string="Tour Line", ondelete='cascade')
    intervention_id = fields.Many2one(
        comodel_name='of.planning.intervention', string="Intervention", ondelete='cascade')
    could_overlap = fields.Boolean(string="Could overlap", readonly=True)
    avoid_check_overlap = fields.Boolean(string="Avoid overlap check", readonly=True)
    multi_employees = fields.Boolean(string="Multi-employees", compute='_compute_multi_employees')
    new_distance = fields.Float(string="Distance (km)")
    new_duration = fields.Float(string="Duration (h)")
    new_date_start = fields.Datetime(string="New start date", readonly=True)
    osrm_query = fields.Text(
        string="OSRM query",
        help="Technical field used to see the full OSRM query used to get the distance and duration")
    geojson_data = fields.Text(
        string="Geojson data", help="Technical field used to display the route on the map")
    endpoint_geojson_data = fields.Text(
        string="Geojson data to the endpoint", help="Technical field used to display the route to the "
        "endpoint on the map")
    endpoint_distance = fields.Float(
        string="Distance to the endpoint (km)",
        help="Technical field used to get the distance to the endpoint (in km)")
    endpoint_duration = fields.Float(
        string="Duration to the endpoint (hours)",
        help="Technical field used to get the duration to the endpoint (in hours)")

    @api.multi
    def _compute_multi_employees(self):
        for line in self:
            line.multi_employees = len(line.intervention_id.employee_ids) > 1
