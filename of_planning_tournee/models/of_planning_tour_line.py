# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
import json
import requests
from dateutil.relativedelta import relativedelta
from odoo import api, models, fields
from odoo.addons.of_utils.models.of_utils import float_2_heures_minutes


ROUTES_AVAILABLE_COLORS = [
    '#0000ff',
    '#3b00f8',
    '#5300f1',
    '#6500ea',
    '#7500e3',
    '#8300db',
    '#8f00d3',
    '#9b00cb',
    '#a500c2',
    '#b000b9',
    '#b900b0',
    '#c200a5',
    '#cb009b',
    '#d3008f',
    '#db0083',
    '#e30075',
    '#ea0065',
    '#f10053',
    '#f8003b',
    '#ff0000'
]

# added fake duplicate colors because the route to first intervention will be in black (harcoded in js)
AVAILABLE_COLORS_TOUR_LINES = [
    '#0000ff',
    '#0000ff',
] + ROUTES_AVAILABLE_COLORS


class OFPlanningTourneeLine(models.Model):
    _name = 'of.planning.tour.line'
    _description = "Tour lines"
    _order = 'tour_id, sequence asc'

    active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", required=True, default=1, copy=False, index=True)
    tour_id = fields.Many2one(comodel_name='of.planning.tournee', string="Tour", required=True, ondelete='cascade')
    intervention_id = fields.Many2one(
        comodel_name='of.planning.intervention', string="Intervention", ondelete='cascade')
    geo_lat = fields.Float(string="Latitude", readonly=True)
    geo_lng = fields.Float(string="Longitude", readonly=True)
    geodata_update_date = fields.Datetime(
        string="Geodata update date", readonly=True,
        help="Technical field to know the last update date of line geodata")
    address_city = fields.Char(string="City", readonly=True)
    previous_geo_lat = fields.Float(string="Latitude of the previous point", compute='_compute_line_data')
    previous_geo_lng = fields.Float(string="Longitude of the previous point", compute='_compute_line_data')
    next_geo_lat = fields.Float(string="Latitude of the next point", compute='_compute_line_data')
    next_geo_lng = fields.Float(string="Longitude of the next point", compute='_compute_line_data')
    is_first_line_of_tour = fields.Boolean(string="First line of the tour", compute='_compute_line_data')
    is_last_line_of_tour = fields.Boolean(string="Last line of the tour", compute='_compute_line_data')
    duration_one_way = fields.Float(string="Trip (h)", copy=False)
    distance_one_way = fields.Float(string="Distance (km)", copy=False)
    last_modification_date = fields.Datetime(
        string="Last modification date", readonly=True, default=False,
        help="Technical field to know the date of the last modification of the line from any wizards "
        "(Optimization or Reorganization)")
    date_before_modification = fields.Datetime(
        string="Date (before modification)", readonly=True, default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)")
    date_deadline_before_modification = fields.Datetime(
        string="Date deadline (before modification)", readonly=True, default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)")
    check_availability_before_modification = fields.Boolean(
        string="Check availability (before modification)", readonly=True, default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)")
    force_date_before_modification = fields.Boolean(
        string="Force date (before modification)", readonly=True, default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)")
    forced_date_before_modification = fields.Datetime(
        string="Forced date (before modification)", readonly=True, default=False,
        help="Technical field that allow restoring the intervention to the state it was before last modification of "
        "its tour line from any wizard (Optimization and Reorganization)")
    hexa_color = fields.Char(string="Hexa color", compute='_compute_line_data')
    # Related fields from intervention
    address_id = fields.Many2one(related='intervention_id.address_id', string="Address", readonly=True)
    date_start = fields.Datetime(related='intervention_id.date', string="Start date", readonly=True)
    employee_ids = fields.Many2many(related='intervention_id.employee_ids', string="Employees", readonly=True)
    flexible = fields.Boolean(related='intervention_id.flexible', string="Flexible", readonly=True)
    duration = fields.Float(related='intervention_id.duree', string="Duration", readonly=True)
    tache_name = fields.Char(related='intervention_id.tache_id.name', readonly=True)
    partner_name = fields.Char(related='intervention_id.partner_id.name', readonly=True)
    address_zip = fields.Char(related='intervention_id.address_id.zip', readonly=True)
    partner_phone = fields.Char(related='intervention_id.partner_id.phone', readonly=True)
    partner_mobile = fields.Char(related='intervention_id.partner_id.mobile', readonly=True)
    map_color_tour = fields.Char(related='intervention_id.map_color_tour', string="Color", readonly=True)
    tour_number = fields.Char(related='intervention_id.tour_number', string="Tour number", readonly=True)
    state = fields.Selection(related='intervention_id.state', string="State", readonly=True)
    # OSRM data for the map
    osrm_query = fields.Text(
        string="OSRM query",
        help="Technical field used to see the full OSRM query used to get the distance and duration")
    geojson_data = fields.Text(
        string="Geojson data",
        help="Geojson data used to draw the line on the map between the previous and the current coordinates")
    endpoint_distance = fields.Float(
        string="Distance to the endpoint (km)",
        help="Technical field used to get the distance to the endpoint (in km)")
    endpoint_duration = fields.Float(
        string="Duration to the endpoint (hours)",
        help="Technical field used to get the duration to the endpoint (in hours)")
    endpoint_geojson_data = fields.Text(
        string="Geojson data to the endpoint",
        help="Geojson data used to draw the line on the map between the last intervention and the endpoint coordinates")

    @api.multi
    def _compute_line_data(self):
        tours = self.mapped('tour_id')
        lines_by_tour = [tour.mapped('tour_line_ids') for tour in tours]
        color_padding_by_tour = {
            tour: max(len(ROUTES_AVAILABLE_COLORS) / len(tour.tour_line_ids), 1) for tour in tours}
        for lines in lines_by_tour:
            lines_sorted = lines.sorted(key=lambda l: (l.tour_id.id, l.sequence))
            len_lines_sorted = len(lines_sorted)
            last_index = 0
            for index, line in enumerate(lines_sorted):
                previous_line = self.env[self._name] if index == 0 else lines_sorted[index - 1]
                next_line = self.env[self._name] if index == len_lines_sorted - 1 else lines_sorted[index + 1]
                is_first_line_of_tour = previous_line == self.env[self._name]
                is_last_line_of_tour = not next_line
                if previous_line:
                    previous_geo_lat = previous_line[-1].geo_lat
                    previous_geo_lng = previous_line[-1].geo_lng
                else:
                    previous_geo_lat = line.tour_id.start_address_id.geo_lat
                    previous_geo_lng = line.tour_id.start_address_id.geo_lng
                if next_line:
                    next_geo_lat = next_line[0].geo_lat
                    next_geo_lng = next_line[0].geo_lng
                else:
                    next_geo_lat = line.tour_id.return_address_id.geo_lat
                    next_geo_lng = line.tour_id.return_address_id.geo_lng
                line.previous_geo_lat = previous_geo_lat
                line.previous_geo_lng = previous_geo_lng
                line.next_geo_lat = next_geo_lat
                line.next_geo_lng = next_geo_lng
                line.is_first_line_of_tour = is_first_line_of_tour
                line.is_last_line_of_tour = is_last_line_of_tour
                color_padding = color_padding_by_tour[line.tour_id]
                sequence = line.sequence - 1
                color_index = last_index + color_padding if sequence > 0 else last_index
                last_index = color_index
                line.hexa_color = AVAILABLE_COLORS_TOUR_LINES[min(color_index, len(AVAILABLE_COLORS_TOUR_LINES)-1)]

    @api.multi
    def _get_time_slot_intervention_label(self, force_date=None, force_start_hour=None, force_end_hour=None):
        """Return the label of the intervention to display in the time slot.
        We can force the date, start hour and stop hour to display the label of a future new intervention

        :param force_date: force the date of the intervention otherwise use intervention date
        :param force_start_hour: force the start hour of the intervention otherwise use intervention start hour
        :param force_end_hour: force the end hour of the intervention otherwise use intervention end hour
        :return: string of time slot label
        :rtype: str
        """
        self.ensure_one()
        intervention = self.intervention_id
        date_intervention = force_date or intervention.date
        start_hour = force_start_hour or intervention.heure_debut_str
        date_intervention = fields.Datetime.context_timestamp(
            intervention, fields.Datetime.from_string(intervention.date)).strftime('%d/%m/%Y')
        if force_end_hour:
            end_hour = force_end_hour
        elif intervention.forcer_dates:
            end_hour = intervention.heure_fin_str
        else:
            # Manage the case where `date_deadline` contains the lunch time.
            # Exemple : Intervention from 12:00:00 to 13:00:00, date_deadline = 13:30:00, that will fake the duration
            # to 1:30:00 instead of 1:00:00.
            # So we need to compute the duration with the real end hour.
            duration = intervention.duree
            hours, minutes = float_2_heures_minutes(duration)
            end_hour = fields.Datetime.context_timestamp(
                intervention, datetime.datetime.strptime(intervention.date, '%Y-%m-%d %H:%M:%S') +
                relativedelta(hours=hours, minutes=minutes)).strftime('%H:%M')
        return '%s %s - %s' % (date_intervention, start_hour, end_hour)

    @api.multi
    def _prepare_optimization_line(self):
        """Prepare data of for the optimization wizard lines

        :return: dict of data to create a optimization wizard line
        :rtype: dict
        """
        self.ensure_one()
        old_time_slot = self._get_time_slot_intervention_label()
        return {
            'tour_id': self.tour_id.id,
            'tour_line_id': self.id,
            'intervention_id': self.intervention_id.id,
            'old_index': self.sequence,
            'old_time_slot': old_time_slot,
            'new_index': False,
            'new_time_slot': False,
            'old_duration': self.duration_one_way,
            'old_distance': self.distance_one_way,
        }

    @api.multi
    def _prepare_reoganization_line(self):
        """Prepare data for the reoganization wizard lines

        :return: dict of data to create a reoganization wizard line
        :rtype: dict
        """
        self.ensure_one()
        return {
            'sequence': self.sequence,
            'old_sequence': self.sequence,
            'tour_id': self.tour_id,
            'tour_line_id': self.id,
            'intervention_id': self.intervention_id.id,
            'geo_lat': self.geo_lat,
            'geo_lng': self.geo_lng,
            'address_city': self.address_city,
            'duration_one_way': self.duration_one_way,
            'distance_one_way': self.distance_one_way,
        }

    @api.multi
    def _update_line_data_from_intervention(self):
        """ Update line geodata from intervention
        """
        self.ensure_one()
        data = self.tour_id._prepare_tour_line(0, self.intervention_id)
        self.write({
            'geo_lat': data['geo_lat'], 'geo_lng': data['geo_lng'], 'address_city': data['address_city'],
            'geodata_update_date': data['geodata_update_date']
        })
        if self.tour_id.ignore_alert_optimization_update:
            self.tour_id.ignore_alert_optimization_update = False

    @api.multi
    def _update_osrm_data(self):
        """ Update the osrm data of the line
        """
        self.ensure_one()
        osrm_base_url = self.env['of.planning.tournee']._get_osrm_base_url()
        if not osrm_base_url or (not self.geo_lat or not self.geo_lng) or (
                not self.previous_geo_lat or not self.previous_geo_lng):
            distance = False
            duration_one_way = False
            osrm_query = False
            geojson_data = False
            endpoint_geojson_data = False
            endpoint_distance = False
            endpoint_duration = False
        else:
            data = self._get_osrm_data_from_line(osrm_base_url)
            distance = data['distance']
            duration_one_way = data['duration']
            osrm_query = data['query']
            geojson_data = data['geojson_data']
            endpoint_geojson_data = data['endpoint_geojson_data']
            endpoint_distance = data['endpoint_distance']
            endpoint_duration = data['endpoint_duration']
        self.write({
            'distance_one_way': distance, 'duration_one_way': duration_one_way, 'osrm_query': osrm_query,
            'geojson_data': geojson_data, 'endpoint_geojson_data': endpoint_geojson_data,
            'endpoint_distance': endpoint_distance, 'endpoint_duration': endpoint_duration})

    @api.model
    def _get_osrm_steps_data(self, full_query=None):
        """ Get the steps data from OSRM

        :param full_query: the full query to OSRM
        :return: tuple of steps, distance, duration
        :rtype: tuple
        """
        if not full_query:
            return []
        try:
            req = requests.get(full_query, timeout=10)
            res = req.json()
        except Exception:
            res = {}
        steps = []
        distance = 0
        duration = 0
        if res.get('routes'):
            route = res['routes'][0]
            distance = route['distance'] / 1000.0
            duration = route['duration'] / 60.0 / 60.0
            legs = route['legs']
            for leg in legs:
                steps += leg['steps']
        return steps, distance, duration

    def _get_osrm_data_from_line(self, osrm_base_url):
        """ Get the OSRM data from the line

        :param osrm_base_url: the base url of OSRM to send the query
        :return: dict of data get from OSRM query that can be used to update the tour line
        :rtype: dict
        """
        endpoint_geojson_data = False
        endpoint_distance = 0
        endpoint_duration = 0
        coords_str = "%s,%s;%s,%s" % (self.previous_geo_lng, self.previous_geo_lat, self.geo_lng, self.geo_lat)
        full_query = '%s/%s?geometries=geojson&steps=true&overview=false' % (osrm_base_url, coords_str)
        steps, distance, duration = self._get_osrm_steps_data(full_query)
        geojson_data = [step['geometry'] for step in steps]
        if self.is_last_line_of_tour:
            coords_str = "%s,%s;%s,%s" % (self.geo_lng, self.geo_lat, self.next_geo_lng, self.next_geo_lat)
            endpoint_full_query = '%s/%s?geometries=geojson&steps=true&overview=false' % (osrm_base_url, coords_str)
            endpoint_steps, endpoint_distance, endpoint_duration = self._get_osrm_steps_data(endpoint_full_query)
            endpoint_geojson_data = [step['geometry'] for step in endpoint_steps]
        geojson_data = geojson_data and json.dumps(geojson_data)
        endpoint_geojson_data = endpoint_geojson_data and json.dumps(endpoint_geojson_data)
        return {
            'query': full_query, 'distance': distance, 'duration': duration, 'geojson_data': geojson_data,
            'endpoint_geojson_data': endpoint_geojson_data, 'endpoint_distance': endpoint_distance,
            'endpoint_duration': endpoint_duration
        }

    @api.model
    def custom_get_color_map_with_preview(self):
        """ Return the custom legend that will be displayed in the bottom right corner of the map

        :return: dict of title and values
        :rtype: dict
        """
        title = ""
        v0 = {'label': u"DI à planifier", 'value': 'green'}
        v1 = {'label': u'Intervention(s) de la tournée', 'value': 'blue'}
        return {'title': title, 'values': (v0, v1)}

    @api.model
    def custom_get_color_map(self):
        """ Return the custom legend that will be displayed in the bottom right corner of the map

        :return: dict of title and values
        :rtype: dict
        """
        title = ""
        v1 = {'label': u"Départ de la tournée", 'value': 'black'}
        v2 = {'label': u"Intervention(s)", 'value': 'blue'}
        v3 = {'label': u"Arrivée de la tournée", 'value': 'black'}
        return {'title': title, 'values': (v1, v2, v3)}

    @api.multi
    def action_restore_intervention_date(self):
        self.ensure_one()
        self.intervention_id.with_context(from_tour_wizard=True).write({
            'date': self.date_before_modification,
            'date_deadline': self.date_deadline_before_modification,
            'date_deadline_forcee': self.forced_date_before_modification,
            'verif_dispo': self.check_availability_before_modification,
            'forcer_dates': self.force_date_before_modification
        })
