# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import json
import logging
import requests
from datetime import datetime, timedelta
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import config


_logger = logging.getLogger(__name__)


AM_LIMIT_FLOAT = 12.0
DEFAULT_MIN_DURATION = 0.5
DEFAULT_PERIOD_IN_DAYS = 30
SECURITY_MARGIN = 10

WEEKDAYS_TR = {
    'Monday': 'mon',
    'Tuesday': 'tue',
    'Wednesday': 'wed',
    'Thursday': 'thu',
    'Friday': 'fri',
    'Saturday': 'sat',
    'Sunday': 'sun',
    # add french keys to avoid error on servers with french language (ie: s-hotel)
    'Lundi': 'mon',
    'Mardi': 'tue',
    'Mercredi': 'wed',
    'Jeudi': 'thu',
    'Vendredi': 'fri',
    'Samedi': 'sat',
    'Dimanche': 'sun'
}


class OFPlanningTournee(models.Model):
    _name = 'of.planning.tournee'
    _inherit = ['of.map.view.mixin', 'of.readgroup']
    _description = "Tour"
    _order = 'date DESC'

    name = fields.Char(string="Name", compute='_compute_tour_name', store=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.today())
    weekday = fields.Selection(
        selection=[
            ('mon', "Monday"),
            ('tue', "Tuesday"),
            ('wed', "Wednesday"),
            ('thu', "Thursday"),
            ('fri', "Friday"),
            ('sat', "Saturday"),
            ('sun', "Sunday")
        ], string="Weekday", compute='_compute_date_weekday', store=True)
    date_min = fields.Date(related='date', string="Date min")
    date_max = fields.Date(related='date', string="Date max")
    state = fields.Selection(selection=[
        ('1-draft', "Draft"),
        ('2-full', "Full"),
        ('3-confirmed', "Confirmed")], string="State", index=True, readonly=True, default='1-draft',
        track_visibility='onchange', copy=False,
        help=" * 'Draft' : With remaining available slots, unconfirmed.\n"
             " * 'Full' : No slots available.\n"
             " * 'Confirmed' : Click on “Confirm” (may or may not have slots available)")
    employee_id = fields.Many2one(
        comodel_name='hr.employee', string=u"Intervenant", required=True, ondelete='cascade')
    start_address_id = fields.Many2one(comodel_name='res.partner', string="Start address")
    return_address_id = fields.Many2one(comodel_name='res.partner', string="Return address")
    employee_other_ids = fields.Many2many(
        comodel_name='hr.employee', relation='tournee_employee_other_rel', column1='tournee_id', column2='employee_id',
        string=u"Équipiers", domain="['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]")
    sector_ids = fields.Many2many(
        comodel_name='of.secteur', relation='tour_sector_rel', column1='tour_id', column2='sector_id',
        string="Sectors", domain="[('type', 'in', ['tech', 'tech_com'])]")
    sector_kanban_names = fields.Text(string=u"Sector names", compute='_compute_sector_kanban_names')
    zip_id = fields.Many2one(comodel_name='res.better.zip', string=u"Ville")
    epi_lat = fields.Float(string=u'Épicentre Lat', digits=(12, 12))
    epi_lon = fields.Float(string=u'Épicentre Lon', digits=(12, 12))
    distance = fields.Float(string=u"Eloignement (km)", digits=(12, 4), default=20.0)
    is_full = fields.Boolean(compute='_compute_is_full', string="Full", store=True, oldname='is_complet')
    is_blocked = fields.Boolean(
        string="Blocked", help="Blocked day : will not be offered for planning", oldname='is_bloque')
    is_confirmed = fields.Boolean(
        string=u"Confirmé", default=True,
        help=u"Une tournée non confirmée sera supprimée si on lui retire ses rendez-vous", oldname='is_confirme')
    is_optimized = fields.Boolean(string="Optimized")
    count_interventions = fields.Integer(string="# Interventions", compute='_compute_count_interventions', store=True)
    intervention_ids = fields.Many2many(
        comodel_name='of.planning.intervention', relation='of_planning_intervention_of_planning_tournee_rel',
        column1='tournee_id', column2='intervention_id', string="Interventions", copy=False)
    tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', inverse_name='tour_id', string="Tour lines", copy=False)
    max_line_sequence = fields.Integer(
        string="Max sequence in lines", compute='_compute_max_line_sequence', store=True)
    total_distance = fields.Float(
        string="Total distance (km)", readonly=True, compute='_compute_total_distance_and_duration', store=True,
        help="Total distance of the tour, that includes the distance to go from the start address and to the stop"
        " address (km)")
    total_duration = fields.Float(
        string="Total duration (h)", readonly=True, compute='_compute_total_distance_and_duration', store=True,
        help="Total duration of the tour, that includes the distance to go from the start address and to the stop"
        " address (h)")
    last_modification_date = fields.Datetime(string="Last modification date", compute='_compute_last_modification_date')
    need_optimization_update = fields.Boolean(
        string="Need new optimization", compute='_compute_need_new_optimization',
        help="Technical field used to alert Users that geodata have changed since the last optimization."
        "If True, the tour needs to be optimized again", store=True)
    ignore_alert_optimization_update = fields.Boolean(string="Ignore alert for optimization update")
    hide_action_buttons = fields.Boolean(
        string="Hide action buttons", compute='_compute_hide_action_buttons',
        help="Technical field used to hide the wizard actions buttons")
    # Map and OSRM routes fields
    additional_records = fields.Text(compute='_compute_additional_records', string="Additionnal records")
    map_tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', compute='_compute_map_tour_line_ids', string="Tour lines")

    # Pour recherche
    gb_sector_id = fields.Many2one(
        comodel_name='of.secteur', compute=lambda *a, **k: {}, search='_search_gb_sector_id', string=u"Secteur",
        of_custom_groupby=True)
    # Verify if we are currently creating the record
    creating = fields.Boolean(string=u"Creating", compute='_compute_creating')

    _sql_constraints = [
        ('date_employee_uniq', 'unique (date,employee_id)',
         u"Il ne peut exister qu'une tournée par employé pour un jour donné")
    ]

    @api.multi
    @api.depends('date', 'employee_id')
    def _compute_tour_name(self):
        for record in self:
            date_str = False
            if record.date:
                date_str = fields.Date.from_string(record.date).strftime('%d/%m/%Y')
            record.name = '%s%s' % (record.employee_id.name, ' - %s' % date_str or '')

    @api.multi
    @api.depends('date')
    def _compute_date_weekday(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for record in self:
            day_value = False
            if record.date:
                local_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(record.date))
                day_value = WEEKDAYS_TR[local_date.strftime('%A').capitalize()]
            record.weekday = day_value

    def _compute_additional_records(self):
        """This is to display the tour start and end address markers on the map
        """
        for tour in self:
            start_marker, end_marker = tour._get_start_stop_markers_data_for_tour()
            tour.additional_records = json.dumps([start_marker, end_marker])

    @api.multi
    @api.depends('tour_line_ids', 'tour_line_ids.intervention_id')
    def _compute_count_interventions(self):
        for tour in self:
            tour.count_interventions = len(tour.tour_line_ids.mapped('intervention_id'))

    @api.multi
    @api.depends('tour_line_ids.geodata_update_date', 'last_modification_date', 'ignore_alert_optimization_update')
    def _compute_need_new_optimization(self):
        for tour in self:
            max_date = max(
                tour.tour_line_ids.mapped('geodata_update_date')) if tour.tour_line_ids else False
            tour.need_optimization_update = max_date > tour.last_modification_date \
                if tour.date >= fields.Date.today() and \
                max_date and \
                tour.last_modification_date and \
                not tour.ignore_alert_optimization_update \
                else False

    @api.multi
    @api.depends('tour_line_ids', 'tour_line_ids.sequence')
    def _compute_map_tour_line_ids(self):
        for tour in self:
            tour.map_tour_line_ids = tour.tour_line_ids.sorted(key=lambda l: l.sequence)

    @api.multi
    def _compute_hide_action_buttons(self):
        for tour in self:
            tour.hide_action_buttons = not tour.tour_line_ids or tour.date < fields.Date.today()

    @api.multi
    @api.depends(
        'tour_line_ids.duration_one_way', 'tour_line_ids.distance_one_way', 'tour_line_ids.endpoint_distance',
        'tour_line_ids.endpoint_duration', 'tour_line_ids.is_last_line_of_tour')
    def _compute_total_distance_and_duration(self):
        for tour in self:
            total_distance = 0
            total_duration = 0
            for line in tour.tour_line_ids:
                total_distance += line.distance_one_way
                total_duration += line.duration_one_way
                if line.is_last_line_of_tour:
                    total_distance += line.endpoint_distance
                    total_duration += line.endpoint_duration
            tour.total_distance = total_distance
            tour.total_duration = total_duration

    @api.multi
    @api.depends('tour_line_ids.last_modification_date')
    def _compute_last_modification_date(self):
        for tour in self:
            dates = [d for d in tour.tour_line_ids.mapped('last_modification_date') if d]
            tour.last_modification_date = max(dates) if dates else False

    @api.multi
    @api.depends(
        'employee_id', 'date', 'is_blocked', 'employee_id.of_tz', 'employee_id.of_tz_offset', 'tour_line_ids',
        'tour_line_ids.intervention_id')
    def _compute_is_full(self):
        """ A tour full is a tour that is in the past or that has no more available slots.
        """
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        today_str = fields.Date.today()
        for tour in self:
            if tour.is_blocked:
                tour.is_full = False
                continue
            if tour.date < today_str:
                tour.is_full = True
                continue

            employee = tour.employee_id
            if employee.of_tz and employee.of_tz != 'Europe/Paris':
                self = self.with_context(tz=employee.of_tz)

            interventions = tour._get_linked_interventions()
            if not interventions or not tour.tour_line_ids:
                tour.is_full = False
                continue

            employee_wh = employee.get_horaires_date(tour.date)[employee.id]
            nb_timeslots = len(employee_wh)
            if nb_timeslots == 0:  # employee is not working, so the tour is full
                tour.is_full = True
                continue

            # build the timeline for occupied timeslots of the day for the employee and check if it is full
            min_duration = self.env['ir.values'].get_default(
                'of.intervention.settings', 'duree_min_creneaux_dispo') or DEFAULT_MIN_DURATION
            day_timeline = tour._get_employee_day_unavailability_timeline(interventions, employee_wh, nb_timeslots)
            is_full = True
            last_end = 0
            for start, end in day_timeline:
                if start - last_end > min_duration:
                    # there is a gap in the timeline so the tour is not full
                    # we consider that a gap of more than 30 min is enough to consider the tour as not full
                    is_full = False
                    break
                if end > last_end:
                    last_end = end
            tour.is_full = is_full

    @api.multi
    @api.depends('tour_line_ids', 'tour_line_ids.sequence')
    def _compute_max_line_sequence(self):
        for tour in self:
            lines = tour.mapped('tour_line_ids.sequence')
            tour.max_line_sequence = lines and max(lines) or 0

    @api.depends('sector_ids')
    def _compute_sector_kanban_names(self):
        for record in self:
            record.sector_kanban_names = " - ".join([sector.name for sector in record.sector_ids])

    # can't put id in depends
    @api.depends('employee_id')
    def _compute_creating(self):
        for record in self:
            record.creating = not isinstance(record.id, int) and not hasattr(record, '_origin')

    def _search_gb_sector_id(self, operator, value):
        return [('sector_ids', operator, value)]

    @api.onchange('zip_id')
    def _onchange_zip_id(self):
        if self.zip_id:
            self.epi_lat = self.zip_id.geo_lat
            self.epi_lon = self.zip_id.geo_lng

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.start_address_id = self.employee_id.of_address_depart_id.id
        self.return_address_id = self.employee_id.of_address_retour_id.id

    @api.multi
    def _get_linked_interventions(self):
        """ Get the interventions of the tour, sorted by date.
        """
        self.ensure_one()
        return self.env['of.planning.intervention'].search([
            ('employee_ids', 'in', self.employee_id.id),
            ('date', '<=', self.date),
            ('date_deadline', '>=', self.date),
            ('state', 'in', ('draft', 'confirm'))], order='date')

    @api.multi
    def _get_start_address(self):
        """ Get the start address of the tour.
        If the tour is linked to an employee, return the employee's start address.
        Otherwise, return address of employee company.

        :return: the start address of tour
        :rtype: recordset res.partner
        """
        self.ensure_one()
        return self.employee_id.of_address_depart_id or self.employee_id.company_id.partner_id

    @api.multi
    def _get_return_address(self):
        """ Get the return address of the tour.
        If the tour is linked to an employee, return the employee's return address.
        Otherwise, return address of employee company.

        :return: the return address of tour
        :rtype: recordset res.partner
        """
        self.ensure_one()
        return self.employee_id.of_address_retour_id or self.employee_id.company_id.partner_id

    @api.model
    def _get_tour_addresses_vals(self, vals):
        """ Get the start and return addresses depending on the tour values.
        If their is no addresses in the values, get the default addresses of the employee or the company.
        If the tour is not linked to an employee, return False for both addresses.

        This method is used in the create method to ensure that the addresses are always set if possible.

        :param vals: tour values from create or write
        :return: a dict with the start and return addresses
        :rtype: dict
        """
        if not vals.get('employee_id'):
            return {'start_address_id': vals.get('start_address_id'), 'return_address_id': vals.get('start_address_id')}

        employee_id = vals.get('employee_id')
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        start_address = vals.get('start_address_id', employee.of_address_depart_id.id or False)
        return_address = vals.get('return_address_id', employee.of_address_retour_id.id or False)
        if not start_address:
            start_address = employee.company_id.partner_id.id or False
        if not return_address:
            return_address = employee.company_id.partner_id.id or False
        return {
            'start_address_id': start_address,
            'return_address_id': return_address,
        }

    @api.multi
    def _get_employee_day_unavailability_timeline(self, interventions, employee_wh, nb_timeslots):
        """ Build the timeline of unavailability, based on
        the employee's working hours and interventions. The timeline starts at 0am and ends at 12pm.

        :param interventions: Intervention of the employee for the day (sorted by date)
        :param employee_wh: Working hours of the employee for the day
        :param nb_timeslots: Number of timeslots of the employee for the day
        :return: Sorted list of tuples (start, end) of the timeline
        :rtype: list
        """
        self.ensure_one()
        date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.date))

        timeline = [(0.0, employee_wh[0][0])]
        timeline.extend((employee_wh[i - 1][1], employee_wh[i][0]) for i in range(1, nb_timeslots))
        timeline.append((employee_wh[-1][1], 24.0))
        day_start = employee_wh[0][0]
        day_end = employee_wh[-1][1]

        # add interventions to the unvailability timeline
        for intervention in interventions:
            start_date_local = fields.Datetime.context_timestamp(
                intervention, fields.Datetime.from_string(intervention.date))
            if start_date_local.day != date_local.day:
                start_flo = day_start
            else:
                start_flo = (start_date_local.hour + start_date_local.minute / 60.0 + start_date_local.second / 3600.0)

            end_date_local = fields.Datetime.context_timestamp(
                intervention, fields.Datetime.from_string(intervention.date_deadline))
            if end_date_local.day != date_local.day:
                end_flo = day_end
            else:
                end_flo = (end_date_local.hour + end_date_local.minute / 60.0 + end_date_local.second / 3600.0)

            timeline.append((start_flo, end_flo))
        timeline.sort()  # chronological order
        return timeline

    @api.multi
    def _get_start_stop_markers_data_for_tour(self):
        """ Return the data of the start and stop markers of the tour.
        They are not real interventions just markers to display on the map.

        :return: Tuple of dict of the markers data
        :rtype: tuple(dict, dict)
        """
        self.ensure_one()
        date_preview = \
            self.date and fields.Datetime.from_string(self.date).strftime('%Y-%m-%d 00:00:00') or False
        default_marker = {
            'id': self.id * -1,  # Negative id to avoid conflict with real interventions on the map
            'last_address_tour': False,
            'tour_number': False,
            'partner_phone': False,
            'partner_mobile': False,
            'date': date_preview,
            'rendered': True
        }
        same_start_return_address = self.start_address_id.geo_lng == self.return_address_id.geo_lng and \
            self.start_address_id.geo_lat == self.return_address_id.geo_lat
        # Start of the tour
        start_marker = default_marker.copy()
        start_marker['number'] = 'start'
        start_marker['iconUrl'] = 'black'
        start_marker['tache_name'] = _("Departure") if not same_start_return_address else _("Departure/Return")
        start_marker['address_city'] = self.start_address_id.city
        start_marker['partner_name'] = self.start_address_id.name
        start_marker['geo_lng'] = self.start_address_id.geo_lng
        start_marker['geo_lat'] = self.start_address_id.geo_lat
        start_marker['address_zip'] = self.start_address_id.zip
        # End of the tour
        end_marker = default_marker.copy()
        end_marker['id'] -= 1  # Remove one to get another id to avoid conflict with the start marker id on the map
        end_marker['number'] = 'stop'
        end_marker['iconUrl'] = 'black'
        end_marker['tache_name'] = _("Return") if not same_start_return_address else _("Departure/Return")
        end_marker['address_city'] = self.return_address_id.city
        end_marker['partner_name'] = self.return_address_id.name
        end_marker['geo_lng'] = self.return_address_id.geo_lng
        end_marker['geo_lat'] = self.return_address_id.geo_lat
        end_marker['address_zip'] = self.return_address_id.zip
        return start_marker, end_marker

    @api.multi
    def _get_tour_coordinates_data(self):
        """ Returns a string of coordinates as "longitude, latitude;..." of the tour.
        Also a dict of a hint string of each coordinates associated to the tour line.
        This dict will be used by wizards to be able to retrieve the tour line associated to the coordinates because
        OSRM will send us this hint string in the response.

        :returns:
            - coordinates_str: String of coordinates as "longitude, latitude;..."
            - tour_data_by_hint: Dict of a hint string of each coordinates associated to the tour line.
        :rtype: tuple
        """
        self.ensure_one()
        # start points
        start_address = self.start_address_id
        if not start_address:
            # if no start address is set on the tour, we take the employee's address or the company's address
            self.start_address_id = self._get_start_address()
        # end points
        stop_address = self.return_address_id
        if not stop_address:
            # if no start address is set on the tour, we take the employee's address or the company's address
            self.return_address_id = self._get_return_address()

        coordinates_str = "%s,%s" % (start_address.geo_lng, start_address.geo_lat)
        hint = self._get_nearest_point_hint(coordinates_str)
        tour_data_by_hint = {
            hint: [{
                'tour': self,
                'line': False,
                'coordinates': (start_address.geo_lng, start_address.geo_lat),
                'intervention_id': False,
                'type': 'start'
            }]
        }

        # get intervention points from the tour lines
        for line in self.tour_line_ids:
            coord_str = "%s,%s" % (line.geo_lng, line.geo_lat)
            hint = self._get_nearest_point_hint(coord_str)
            coordinates_str += ";%s" % coord_str
            if not tour_data_by_hint.get(hint):
                tour_data_by_hint[hint] = []
            tour_data_by_hint[hint].append({
                'tour': self,
                'line': line,
                'coordinates': (line.geo_lng, line.geo_lat),
                'intervention_id': line.intervention_id.id,
                'type': 'intervention'})

        coord_str = "%s,%s" % (stop_address.geo_lng, stop_address.geo_lat)
        hint = self._get_nearest_point_hint(coord_str)
        coordinates_str += ";%s" % coord_str
        tour_data_by_hint[hint] = [{
            'tour': self,
            'line': False,
            'intervention_id': False,
            'coordinates': (stop_address.geo_lng, stop_address.geo_lat),
            'type': 'end'}]

        return coordinates_str, tour_data_by_hint

    @api.model
    def _get_osrm_base_url(self, mode='route'):
        """ Returns the OSRM server base URL depending on the mode ('route', 'trip' or 'nearest')

        :param mode: 'route', 'trip' or 'nearest'
        :return: OSRM server base URL
        :rtype: str
        """
        routing_base_url = config.get('of_routing_base_url', '')
        routing_version = config.get('of_routing_version', '')
        routing_profile = config.get('of_routing_profile', '')
        if not routing_base_url or not routing_version or not routing_profile:
            return False
        return '%s%s/%s/%s' % (routing_base_url, mode, routing_version, routing_profile)

    @api.multi
    def _test_osrm_connection(self):
        """ Test the connection to the OSRM server.
        :return: OSRM server response
        :rtype: dict
        """
        self.ensure_one()
        test_query = '%s/%s?number=1' % (self._get_osrm_base_url('nearest'), '-1.72323900,48.17292300.json')
        try:
            req = requests.get(test_query, timeout=10)
            res = req.json()
        except requests.exceptions.ConnectionError as e:
            raise UserError(_("Error connecting to OSRM server, please try again later.\n\n%s") % e)
        except Exception as e:
            raise UserError(_("An error has occured during the connection to the OSRM server : %s") % e)
        return res

    def _get_nearest_point_hint(self, coordinate=None):
        """ Returns the hint string of the nearest point to given coordinate.

        :param coordinate: Coordinates of a point as "longitude, latitude"
        :return: the hint string of the nearest point to the coordinate
        :rtype: str
        """
        if coordinate is None:
            return False

        hint_query = '%s/%s?number=1' % (self._get_osrm_base_url('nearest'), coordinate)
        try:
            req = requests.get(hint_query, timeout=10)
            res = req.json()
        except Exception:
            res = {}
        return res.get('waypoints')[0].get('hint') if res.get('code') == 'Ok' else {}

    def _send_osrm_trip_request(self, coordinates_str=None):
        """Start a 'trip' request to the OSRM server.
        The 'trip' plugin solves the Traveling Salesman Problem using a greedy heuristic (farthest-insertion algorithm).
        Returned path does not have to be the exact fastest one, as TSP is NP-hard it is only an approximation.

        :param coordinates_str: String of coordinates as "longitude, latitude;..." of the tour
        :return: request result
        :rtype: dict
        """
        self.ensure_one()

        osrm_url = self._get_osrm_base_url('trip')
        if not osrm_url:
            return {}

        if not coordinates_str:
            coordinates_str = self._get_str_tour_coordinates()

        # request
        full_query = osrm_url + '/' + coordinates_str
        full_query += '?geometries=geojson&overview=simplified&roundtrip=false&source=first&destination=last'
        # roundtrip: return to the first location, default is true but we set it to false because in some cases
        # the start and end points could be different.
        # source: start at the first location
        # destination: end at the last location
        # see http://project-osrm.org/docs/v5.24.0/api/#trip-service for more details
        try:
            req = requests.get(full_query, timeout=10)
            res = req.json()
        except Exception:
            res = {}
        return res

    @api.multi
    def _prepare_tour_line(self, idx, intervention):
        """ Prepare the values to create a tour line.

        :param idx: wanted sequence of the tour line
        :param intervention: intervention to link to the tour line
        :return: the values to create a tour line
        :rtype: dict
        """
        self.ensure_one()
        intervention = intervention.with_context(active_tour_id=self.id)
        geo_lat = intervention.geo_lat
        geo_lng = intervention.geo_lng
        address_city = intervention.address_city
        return {
            'sequence': idx,
            'tour_id': self.id,
            'intervention_id': intervention.id,
            'geo_lat': geo_lat,
            'geo_lng': geo_lng,
            'address_city': address_city,
            'geodata_update_date': fields.Datetime.now(),
            'duration_one_way': False,
            'distance_one_way': False
        }

    @api.multi
    def _get_employee_hours(self):
        """Returns the employee's working hours on the day of the tour.
        """
        self.ensure_one()
        hours = self.employee_id.get_horaires_date(self.date)[self.employee_id.id] if self.employee_id else []
        # we want to return a list of tuples (start, end) of working hours, so we need to manage the case where
        # the employee has only one or more than two slots of working hours
        if len(hours) == 1:
            half_day = hours[0][1] - hours[0][0]
            just_before_half_day = half_day - 0.01
            hours = [[(hours[0][0], just_before_half_day)], [(half_day, hours[0][1])]]
        elif len(hours) > 2:
            new_hours = [[], []]
            for slot in hours:
                if slot[0] < AM_LIMIT_FLOAT:
                    new_hours[0].append(slot)
                else:
                    new_hours[1].append(slot)
            hours = new_hours
        else:
            hours = [[hours[0]], [hours[1]]]
        return hours

    @api.multi
    def _is_working_hours_disrupted(self):
        """Check if the employee's working hours are disrupted on the day of the tour.
        For example, if the employee has a working hours of 8:00-12:30 and 13:45-17:00 and an intervention
        start at 12:30 and end at 13:45, the employee's working hours are disrupted.

        :returns:
            - True if the employee's working hours are disrupted, False otherwise
            - The number of disruptions
        :rtype: tuple(bool, int)
        """
        self.ensure_one()
        if not self.tour_line_ids:
            return False, 0

        employee_wh = self._get_employee_hours()
        if len(employee_wh[0]) > 1 or len(employee_wh[1]) > 1:
            # we don't want to manage the case where the employee has more than 2 slots of working hours
            return False, 0

        if not employee_wh:
            # maybe the employee has working hours but not on the day of the tour
            raise UserError(_(
                "Employee \"%s\" has no working hours for this day.\n") %
                self.employee_id.name)

        end_am = employee_wh[0][0][1]
        start_pm = employee_wh[1][0][0]
        # get the start and end hours of interventions on the tour
        interventions_dates = self.tour_line_ids.mapped(
            lambda tl: (
                fields.Datetime.context_timestamp(tl, fields.Datetime.from_string(tl.intervention_id.date)),
                fields.Datetime.context_timestamp(tl, fields.Datetime.from_string(tl.intervention_id.date_deadline))
            )
        )
        # convert hours to float numbers
        interventions_hours_float = map(
            lambda idates: (
                round(idates[0].hour + idates[0].minute / 60.0 + idates[0].second / 3600.0, 5),
                round(idates[1].hour + idates[1].minute / 60.0 + idates[1].second / 3600.0, 5)
            ), interventions_dates
        )
        # check if some interventions are outside the working hours
        interventions_outside_working_hours = map(
            lambda ihours: (
                (ihours[0] <= end_am and ihours[1] > end_am)
                or (ihours[0] > end_am and ihours[1] < start_pm)
                or (start_pm > ihours[0] > end_am and ihours[1] > start_pm)
                or (ihours[0] < end_am and ihours[1] > start_pm)
            ),
            interventions_hours_float,
        )
        # count them
        count = len(filter(lambda x: x, interventions_outside_working_hours))
        # return True if there is at least one intervention outside the working hours
        return any(interventions_outside_working_hours), count

    @api.multi
    def _get_float_first_tour_hour(self):
        """Return the first hour of the tour as a float number.
        :return: hour in float number
        :rtype: float
        """
        self.ensure_one()
        if not self.tour_line_ids:
            return False
        # voluntary sorted by date_start, untrust the sequence (database alteration for example)
        first_intervention = self.tour_line_ids.sorted(key=lambda tl: tl.date_start)[0]
        start_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(first_intervention.date_start))
        return round(
            start_date.hour + start_date.minute / 60.0 + start_date.second / 3600.0, 5)

    @api.multi
    def _get_float_first_afternoon_tour_hour(self):
        """Return the first hour of the afternoon of the tour as a float number.
        :return: hour in float number
        :rtype: float
        """
        self.ensure_one()
        if not self.tour_line_ids:
            return False

        # get hours of the employee for the afternoon
        employee_wh = self._get_employee_hours()
        complex_hours = len(employee_wh[0]) > 1
        afternoon_hours = (
            employee_wh[1][0]
            if complex_hours
            else [h[0][0] for h in employee_wh if h[0][0] > AM_LIMIT_FLOAT]
        )
        if not afternoon_hours:
            return AM_LIMIT_FLOAT

        # build a list of booleans to know if the line is after the afternoon hours
        lines_dates = self.tour_line_ids.mapped(
            lambda tl: fields.Datetime.context_timestamp(tl, fields.Datetime.from_string(tl.date_start)))
        afternoon_lines = map(
            lambda ds: round(ds.hour + ds.minute / 60.0 + ds.second / 3600.0, 5) >= afternoon_hours[0], lines_dates)
        # get the index of the first line after the afternoon hours or return AM_LIMIT_FLOAT if not found
        try:
            first_afternoon_line = afternoon_lines.index(True)
        except ValueError:
            return AM_LIMIT_FLOAT

        first_afternoon_dt = fields.Datetime.context_timestamp(
            self, fields.Datetime.from_string(self.tour_line_ids[first_afternoon_line].date_start))
        return round(
            first_afternoon_dt.hour + first_afternoon_dt.minute / 60.0 + first_afternoon_dt.second / 3600.0, 5)

    def _check_employees_working_hours(self):
        """Check if at least one employee has no working hours on the day of the tour.
        This may happen if the tour employee works with other people on an intervention.

        :raises UserError: if at least one employee has no working hours on the day of the tour.
        :return: True
        :rtype: bool
        """
        self.ensure_one()

        employees = self.tour_line_ids.mapped('intervention_id.employee_ids')
        employees_wo_segment_ids = employees.filtered(lambda e: not e.of_segment_ids)
        if employees_wo_segment_ids:
            if len(employees_wo_segment_ids) > 1:
                message = _(
                    "Employees \"%s\" have no working hours.\n"
                    "Please set the working hours before optimizing/reorganizing the tour") % (
                        ', '.join(employees_wo_segment_ids.mapped('name')))
            else:
                message = _(
                    "Employee \"%s\" has no working hours.\n"
                    "Please set the working hours before optimizing/reorganizing the tour") % \
                    employees_wo_segment_ids.name
            raise UserError(message)
        return True

    def _check_and_update_tour_addresses(self):
        """Check if the tour has a start and an end address.
        Updates them if they are not set and if its possible.

        :raises UserError: if the tour has no start address or if the tour has no end address.
        """
        self.ensure_one()
        start_address = self.start_address_id
        return_address = self.return_address_id
        updates_addresses = False
        if not start_address:
            start_address = self._get_start_address()
            updates_addresses = True
        if not return_address:
            return_address = self._get_return_address()
            updates_addresses = True
        if not start_address:
            raise UserError(_("Please set the start address before optimizing/reorganizing the tour."))
        if not return_address:
            raise UserError(_("Please set the return address before optimizing/reorganizing the tour."))
        if updates_addresses:
            self.start_address_id = start_address
            self.return_address_id = return_address
            self.action_compute_osrm_data()

    def _check_interventions_addresses(self):
        """Check if at least one line needs to be updated with OSRM data. If yes, update it.
        :raises UserError: if at least one intervention has no address or if at least one address has no geolocation.
        :return: True
        :rtype: bool
        """
        self.ensure_one()

        if any(not line.intervention_id.address_id for line in self.tour_line_ids):
            raise UserError(_("You must set the address of all interventions before optimizing/reorganising the tour."))
        if any(
                not line.intervention_id.address_id.geo_lat and not line.intervention_id.address_id.geo_lng
                for line in self.tour_line_ids):
            raise UserError(_("Please geolocate all addresses before optimizing/reorganising the tour."))
        return True

    def _check_missing_osrm_data(self, force=False):
        """Check if the at least one line needs to be updated with OSRM data. If yes, update it.

        :param force: force the tour lines data update
        :param reload: reload the tour lines data update with intervention data
        :return: None
        """
        self.ensure_one()
        # get the tour route from OSRM if at least one tour line has missing data
        if not self.start_address_id or not self.return_address_id:
            self._check_and_update_tour_addresses()  # will call action_compute_osrm_data if needed
        elif force or self.need_optimization_update or not self.total_distance or not self.total_duration or any(
                not line.geojson_data or not line.distance_one_way or not line.duration_one_way
                for line in self.tour_line_ids):
            self.action_compute_osrm_data()

    @api.multi
    def _reorder_tour_lines(self):
        """ Reorder the tour lines depending on the tour lines interventions dates
        """
        for tour in self:
            tour.map_tour_line_ids = tour.tour_line_ids.sorted(key=lambda l: l.intervention_id.date)
            tour._reset_sequence()

    @api.multi
    def _reset_sequence(self):
        """ Reset the tour lines sequence depending on each line date_start.
        """
        for tour in self:
            for current_sequence, line in enumerate(tour.tour_line_ids.sorted(key=lambda l: l.date_start), start=1):
                line.sequence = current_sequence

    @api.multi
    def _set_tour_to_draft(self):
        """ Set the tour state to 'draft' if it is flagged as 'incomplete' and if the tour state is 'full'.
        We don't want to set the tour state to 'draft' if it is already at 'draft' or 'confirmed'.
        """
        tours = self.filtered(lambda t: not t.is_full and t.state == '2-full')
        tours and tours.write({'state': '1-draft'})

    @api.multi
    def _set_tour_to_full(self):
        """ Set the tour state to 'full' if it is flagged as 'complete' and if the tour state is 'draft'.
        We don't want to set the tour state to 'full' if it is already at 'full' or 'confirmed'.
        """
        tours = self.filtered(lambda t: t.is_full and t.tour_line_ids and t.state == '1-draft')
        tours and tours.write({'state': '2-full'})

    @api.multi
    def _populate_tour_lines(self, delete_all=False, reset_sequence=True):
        """ Populates the tour lines.
        It allows to delete all the tour lines beforehand if needed. It may also reset the tour lines sequence after
        creating new lines.

        :param delete_all: if True, delete all the tour lines before creating new ones
        :param reset_sequence: if True, reset the tour lines sequence after creating new lines
        """
        for tour in self:
            if delete_all:
                tour.tour_line_ids.sudo().unlink()
            # get the interventions that should not be in the tour anymore
            interventions_to_remove = self._get_interventions_to_remove(tour)
            if interventions_to_remove and tour.date >= fields.Date.today():
                tour.sudo().write({'tour_line_ids': [(5, 0, interventions_to_remove.ids)]})
            # get the interventions that are not already in the tour
            interventions = self._get_interventions_to_add(tour)
            if interventions and tour.date >= fields.Date.today() or self._context.get('force_restore'):
                index = 1 if delete_all or not tour.tour_line_ids else tour.max_line_sequence + 1
                lines = [
                    (0, 0, tour._prepare_tour_line(idx, intervention))
                    for idx, intervention in enumerate(interventions, index)]
                tour.write({'tour_line_ids': lines})
                if reset_sequence:
                    tour._reset_sequence()

    def _get_interventions_to_add(self, tour):
        """ Get the interventions that are not already in the tour to add them if needed.
        """
        interventions = tour._get_linked_interventions()
        return interventions - tour.tour_line_ids.mapped('intervention_id')

    def _get_interventions_to_remove(self, tour):
        """ Get the interventions that should not be in the tour anymore.
        """
        interventions = tour._get_linked_interventions()
        return tour.tour_line_ids.mapped('intervention_id') - interventions

    @api.multi
    def copy(self, default=None):
        """ Limit the copy of a tour to the force_copy context key.
        The tour copy should be available in the futur with a specific wizard.
        Currently has no sense to copy a tour because of we don't copy the tour lines.
        To avoid the constraint error display, we raise a UserError.
        """
        if self._context.get('force_copy'):
            default = dict(default or {}, date=fields.Date.today())
            return super(OFPlanningTournee, self).copy(default)
        raise UserError(_("You can't duplicate a tour."))

    @api.model
    def create(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        # @todo: vérifier pertinence du champ is_blocked avec aymeric
        if vals.get('is_blocked'):
            if intervention_obj.search([('date', '>=', vals['date']), ('date', '<=', vals['date']),
                                        ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                        ('employee_ids', 'in', vals['employee_id'])]):
                raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')

        # Set Tour addresses (from vals or employee_id) if not set cause thoses fields are required only in view and
        # tour can be created by cron also
        vals.update(self._get_tour_addresses_vals(vals))
        return super(OFPlanningTournee, self).create(vals)

    @api.multi
    def write(self, vals):
        if ('start_address_id' in vals and not vals.get('start_address_id')) or (
                'return_address_id' in vals and not vals.get('return_address_id')):
            # we don't want to remove the start or end address of a tour
            if 'start_address_id' in vals:
                del vals['start_address_id']
            if 'return_address_id' in vals:
                del vals['return_address_id']

        intervention_obj = self.env['of.planning.intervention']
        for tournee in self:
            if vals.get('is_blocked', tournee.is_blocked):
                date_intervention = vals.get('date', tournee.date)
                employee_id = vals.get('employee_id', tournee.employee_id.id)
                if intervention_obj.search([('date', '>=', date_intervention), ('date', '<=', date_intervention),
                                            ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                            ('employee_ids', 'in', employee_id)]):
                    raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')

        result = super(OFPlanningTournee, self).write(vals)
        if self._context.get('reset_sequence'):
            self._reset_sequence()
        return result

    @api.multi
    def _write(self, values):
        saved_values = {
            tour.id: {'start_address_id': tour.start_address_id, 'return_address_id': tour.return_address_id}
            for tour in self
        }
        res = super(OFPlanningTournee, self)._write(values)
        # Low level implementation to ensure that we will update the tour state after computing fields.
        states_fields_to_check = ['is_full', 'is_blocked', 'state']
        if any(field in values for field in states_fields_to_check):
            self._set_tour_to_draft()
            self._set_tour_to_full()
        address_fields_to_check = ['start_address_id', 'return_address_id']
        if any(field in values for field in address_fields_to_check) and \
                not self._context.get('skip_osrm_data_compute'):
            tours_to_compute = self.env['of.planning.tournee']
            for tour in self:
                old_values = saved_values[tour.id]
                if tour.start_address_id != old_values['start_address_id'] \
                        or tour.return_address_id != old_values['return_address_id']:
                    tours_to_compute |= tour
            tours_to_compute and tours_to_compute.action_compute_osrm_data()
        return res

    @api.multi
    def action_update_map_and_reload(self):
        self.ensure_one()
        self.action_compute_osrm_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
    def action_compute_osrm_data(self, reload=False):
        """ Compute the osrm data for all the tour lines.
        If there is no tour line, it will create them before computing the osrm data.
        """
        for tour in self:
            if not tour.tour_line_ids:
                tour._populate_tour_lines()
            for line in tour.tour_line_ids:
                if reload:
                    line._update_line_data_from_intervention()
                line._compute_line_data()  # keep line updated with the right data
                line._update_osrm_data()
            tour._compute_map_tour_line_ids()

    @api.multi
    def action_restore_tour(self):
        """ Restore the intervention dates to their original values before the tour optimization.
        """
        self.ensure_one()
        current_states = {
            intervention: intervention.state for intervention in self.tour_line_ids.mapped('intervention_id')}
        self.tour_line_ids.mapped('intervention_id').with_context(
            from_tour_wizard=True).write({'state': 'being_optimized'})
        for line in self.tour_line_ids:
            line.action_restore_intervention_date()
        self.tour_line_ids.write({'last_modification_date': False})
        for intervention, state in current_states.items():
            intervention.with_context(from_tour_wizard=True).write({'state': state})
        self._reset_sequence()
        self.with_context(force_restore=True).action_compute_osrm_data()

    @api.multi
    def action_optimize_tour(self):
        """ Open the wizard to optimize the tour.

            :return: the action to open the wizard
        """
        self.ensure_one()
        if not self.tour_line_ids:
            raise UserError(_("You can't optimize an empty tour."))

        optimization_wizard_obj = self.env['of.tour.planning.optimization.wizard']

        # check start and end addresses
        self._check_and_update_tour_addresses()

        # check if employees have working hours
        self._check_employees_working_hours()

        # check if interventions have addresses
        self._check_interventions_addresses()

        # get the route of the tour from OSRM if at least one tour line has missing data
        self._check_missing_osrm_data()

        # create the optimization wizard
        lines_values = [(0, 0, tour_line._prepare_optimization_line()) for tour_line in self.tour_line_ids]
        wizard = optimization_wizard_obj.create({
            'tour_id': self.id,
            'line_ids': lines_values,
        })
        return wizard.action_open(custom_title=self.name)

    @api.multi
    def action_reorganize_tour(self):
        """ Open the wizard to reorganize the tour.

            :return: the action to open the wizard
        """
        self.ensure_one()
        if not self.tour_line_ids:
            raise UserError(_("You can't reorganize an empty tour."))

        reorganize_wizard_obj = self.env['of.tour.planning.reorganization.wizard']

        # check start and end addresses
        self._check_and_update_tour_addresses()

        # check if employees have working hours
        self._check_employees_working_hours()

        # check if interventions have addresses
        self._check_interventions_addresses()

        # get the route of the tour from OSRM if at least one tour line have missing data
        self._check_missing_osrm_data()

        # create the optimization wizard
        lines_values = [(0, 0, tour_line._prepare_reoganization_line()) for tour_line in self.tour_line_ids]
        wizard = reorganize_wizard_obj.create({
            'tour_id': self.id,
            'line_ids': lines_values,
        })
        return wizard.action_open(custom_title=self.name)

    @api.multi
    def action_view_interventions(self):
        """ Open the interventions linked to the tour.

            :return: the action to open linked interventions
        """
        return {
            'name': _("Interventions"),
            'type': 'ir.actions.act_window',
            'res_model': 'of.planning.intervention',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.tour_line_ids.mapped('intervention_id').ids)],
        }

    @api.multi
    def action_confirm_tour(self):
        """ Confirm the tour.
        """
        self.ensure_one()
        self.write({'state': '3-confirmed'})

    @api.multi
    def action_set_back_draft(self):
        """ Set the tour as fradt.
        """
        self.ensure_one()
        self.write({'state': '1-draft'})

    @api.multi
    def action_set_back_full(self):
        """ Set the tour as full.
        """
        self.ensure_one()
        self.write({'state': '2-full'})

    @api.multi
    def action_ignore_alert_optimization_update(self):
        """ Ignore the alert about tour optimization until the next tour modification.
        """
        self.ensure_one()
        self.write({'ignore_alert_optimization_update': True})

    @api.model
    def generate_tour(self, date=False, employee=False):
        """ Generate a tour for the given date/employee if needed, return it otherwise.

        :param date: tour date
        :param employee: tour employee
        :return: the tour
        :rtype: recordset of.planning.tournee
        """
        if not date or not employee:
            return False
        # use sudo() to avoid access rights issues if this method is not called from a cron
        tour = self.sudo().search([('date', '=', date), ('employee_id', '=', employee.id)], limit=1)
        if tour:
            return tour
        tour = self.sudo().create({
            'employee_id': employee.id,
            'date': date,
        })
        # if tour already has interventions, update the tour lines
        if tour.intervention_ids and not tour.tour_line_ids:
            tour._populate_tour_lines()
        return tour

    @api.model
    def cron_generate_tour(self, force_date=False, force_company_id=False):
        """
        This method is called by a cron.

        Generates tours in the futur (if they don't exist) depending on the settings (employees, days, period).
        It will check everyday if there are new employees and create their tours until next period start.

        :param force_date: the date to use instead of today
        :param force_company_id: the company to use instead of the current one
        :return: True
        """
        icp_obj = self.env['ir.config_parameter']
        employee_obj = self.env['hr.employee']
        days_obj = self.env['of.jours']
        ir_values_obj = self.env['ir.values']

        new_employees = employee_obj
        today = datetime.strptime(force_date, '%Y-%m-%d').date() if force_date else datetime.now().date()
        # we are using config parameters here to avoid cron autolock during job processing
        cron_lastcreation = icp_obj.get_param(
            'of.planning.tour.cron_generate_lastcreation', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        lastcreation_d = datetime.strptime(cron_lastcreation, '%Y-%m-%d %H:%M:%S').date()
        cron_nextcall = icp_obj.get_param('of.planning.tour.cron_generate_nextcall', False)
        cron_nextcall_dt = datetime.strptime(cron_nextcall, '%Y-%m-%d %H:%M:%S') if cron_nextcall else False
        if cron_nextcall_dt and cron_nextcall_dt.strftime('%Y-%m-%d') > today.strftime('%Y-%m-%d'):
            # cron is not due to run today but if there is new employees we need to generate tours for them
            new_employees = employee_obj.search([('create_date', '>=', cron_lastcreation)])
            if not new_employees:
                _logger.info('Nothing todo. Cron generate tour is scheduled for %s' % cron_nextcall)
                return True

        company_id = int(force_company_id) if force_company_id else False
        employee_ids = ir_values_obj.get_default('of.intervention.settings', 'tour_employee_ids') or []
        day_ids = ir_values_obj.get_default('of.intervention.settings', 'tour_day_ids') or []
        period_in_days = ir_values_obj.get_default(
            'of.intervention.settings', 'nbr_days_tour_creation') or DEFAULT_PERIOD_IN_DAYS

        if not new_employees:
            employee_domain = [('id', 'in', employee_ids)] if employee_ids else []
            if company_id:
                employee_domain.append('|', ('company_id', '=', company_id), ('company_id', '=', False))
            employees = employee_obj.search(employee_domain)
        elif employee_ids:
            return True  # we don't need to generate tours for new employees if we have a list of employees
        else:
            employees = new_employees

        days = days_obj.search([('id', 'in', day_ids)])
        days_number = [jour.numero for jour in days] or range(1, 8)

        # we have a 10 days margin to ensure we have tours in advance for the next period before the cron is run
        delta = timedelta(days=period_in_days)
        tour_dates = []
        # filter dates to keep only the ones that are in the futur and that are in the days_number list
        for date in [lastcreation_d + timedelta(days=i) for i in range(1, delta.days + 1 + SECURITY_MARGIN)]:
            tour_dates.append(date.strftime('%Y-%m-%d')) if date.weekday() + 1 in days_number else None

        # search existing tours for employees on this period
        if tour_dates:
            search_existing_tours = self.search([
                ('date', '>=', tour_dates[0]), ('date', '<=', tour_dates[-1]), ('employee_id', 'in', employees.ids)])
            tour_by_employee = {}
            for tour in search_existing_tours:
                tour_by_employee.setdefault(tour.employee_id, []).append(tour.date)

            # generate tours for each employee for missing dates
            for employee in employees:
                employee_tour_dates = tour_dates[:]  # copy the list
                if tour_by_employee.get(employee):
                    employee_tour_dates = [x for x in employee_tour_dates if x not in tour_by_employee.get(employee)]

                for date in employee_tour_dates:
                    # create tour
                    self.generate_tour(date, employee)

        # set the nextcall date (in x days)
        cron_nextcall_dt = datetime.strptime(cron_nextcall, '%Y-%m-%d %H:%M:%S') if cron_nextcall else datetime.now()
        cron_generate_nextcall = (cron_nextcall_dt + timedelta(days=period_in_days)).strftime('%Y-%m-%d %H:%M:%S')
        if not new_employees:  # normal cron call
            icp_obj.set_param(
                'of.planning.tour.cron_generate_lastcreation', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            icp_obj.set_param('of.planning.tour.cron_generate_nextcall', cron_generate_nextcall)
            _logger.info('Done. Cron generate tour is scheduled for %s' % cron_generate_nextcall)
        else:  # cron call for new employees
            _logger.info(
                'Done. Cron generate tour for new employees %s. Next call is still scheduled on %s' % (
                    new_employees, cron_generate_nextcall))
        return True

    @api.model
    def _read_group_process_groupby(self, gb, query):
        # Ajout de la possibilité de regrouper par employé
        if gb != 'gb_sector_id':
            return super(OFPlanningTournee, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'tour_sector_rel', 'id', 'tour_id', 'sector_ids'),
            implicit=False, outer=True,
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".sector_id' % (alias,)
        }
