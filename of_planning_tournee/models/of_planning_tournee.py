# -*- coding: utf-8 -*-
import json
import requests
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.tools import config


WEEKDAYS_TR = {
    'Monday': _('Monday'),
    'Tuesday': _('Tuesday'),
    'Wednesday': _('Wednesday'),
    'Thursday': _('Thursday'),
    'Friday': _('Friday'),
    'Saturday': _('Saturday'),
    'Sunday': _('Sunday'),
    # add french keys to avoid error on servers with french language (s-hotel)
    'lundi': _('Monday'),
    'mardi': _('Tuesday'),
    'mercredi': _('Wednesday'),
    'jeudi': _('Thursday'),
    'vendredi': _('Friday'),
    'samedi': _('Saturday'),
    'dimanche': _('Sunday'),
}


class OFPlanningTournee(models.Model):
    _name = 'of.planning.tournee'
    _inherit = 'of.map.view.mixin'
    _description = u"Tournée"
    _order = 'date DESC'

    @api.model_cr_context
    def _auto_init(self):
        """This _auto_init can be deleted on the next update, it forces the recompute of the SaleOrder fields
        'of_laying_week' and 'of_laying_date'
        We moved the version of the module to '10.0.2.0.0' for this update"""
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_planning_tournee')])
        actions_todo = module_self and module_self.latest_version < '10.0.2.1.0' or False

        self._cr.execute(
            "SELECT * FROM information_schema.columns  WHERE table_name = %s AND column_name = 'name'", (self._table,))
        name_exists = self._cr.fetchone()
        res = super(OFPlanningTournee, self)._auto_init()
        if actions_todo and not name_exists:
            tours_with_date = self.search([('date', '!=', False)])
            # Force the computation of the field 'name' for all the tours
            tours_with_employees = tours_with_date.filtered(lambda t: t.employee_id)
            tours_with_employees._compute_tour_name()
            # Cause of existing tours we have to apply the constraint manually
            self._cr.execute("ALTER TABLE of_planning_tournee ALTER name SET NOT NULL;")
            # Force the computation of the weekday
            tours_with_date._compute_date_weekday()
        return res

    name = fields.Char(string="Name", required=True, compute="_compute_tour_name", store=True)
    date = fields.Date(string='Date', required=True)
    weekday = fields.Char(string='Weekday', compute='_compute_date_weekday', store=True)
    date_min = fields.Date(related="date", string="Date min")
    date_max = fields.Date(related="date", string="Date max")
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('full', 'Full'),
            ('confirmed', 'Confirmed'),
        ], string='State', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False,
        help=" * 'Draft' : With remaining available slots, unconfirmed.\n"
             " * 'Full' : No slots available.\n"
             " * 'Confirmed' : Click on “Confirm” (may or may not have slots available)")
    employee_id = fields.Many2one('hr.employee', string=u'Intervenant', required=True, ondelete='cascade')
    start_address_id = fields.Many2one(
        comodel_name='res.partner', string='Start address', compute='_compute_tour_address_start_return',
        inverse='_set_start_address_id', store=True)
    return_address_id = fields.Many2one(
        comodel_name='res.partner', string='Return address', compute='_compute_tour_address_start_return',
        inverse='_set_return_address_id', store=True)
    employee_other_ids = fields.Many2many(
        comodel_name='hr.employee', relation='tournee_employee_other_rel', column1='tournee_id', column2='employee_id',
        string=u'Équipiers', domain="['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]")
    secteur_id = fields.Many2one('of.secteur', string='Secteur', domain="[('type', 'in', ['tech', 'tech_com'])]")
    zip_id = fields.Many2one('res.better.zip', 'Ville')
    epi_lat = fields.Float(string=u'Épicentre Lat', digits=(12, 12))
    epi_lon = fields.Float(string=u'Épicentre Lon', digits=(12, 12))
    distance = fields.Float(string='Eloignement (km)', digits=(12, 4), default=20.0)
    is_complet = fields.Boolean(compute="_compute_is_complet", string='Complet', store=True)
    is_bloque = fields.Boolean(string=u'Bloqué', help=u'Journée bloquée : ne sera pas proposée à la planification')
    is_confirme = fields.Boolean(
        string=u'Confirmé', default=True,
        help=u'Une tournée non confirmée sera supprimée si on lui retire ses rendez-vous')
    is_optimized = fields.Boolean(string='Optimized')
    intervention_ids = fields.Many2many(
        'of.planning.intervention', 'of_planning_intervention_of_planning_tournee_rel', 'tournee_id', 'intervention_id',
        string='Interventions')
    tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', inverse_name='tour_id', string='Tour lines')
    max_line_sequence = fields.Integer(
        string='Max sequence in lines', compute='_compute_max_line_sequence', store=True)
    # Map and OSRM routes fields
    markers_to_preview = fields.Text(compute='_compute_markers_to_preview', string='Markers to preview')
    map_tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', inverse_name='tour_id', string='Tour lines')
    test_map_tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', inverse_name='tour_id', string='Tour lines')
    osrm_route_steps = fields.Text(string='OSRM route steps')

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
            day_str = ''
            if record.date:
                local_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(record.date))
                day_str = WEEKDAYS_TR[local_date.strftime('%A')]
            record.weekday = day_str

    @api.multi
    @api.depends('employee_id')
    def _compute_tour_address_start_return(self):
        for record in self:
            if record.employee_id:
                record.start_address_id = record.employee_id.of_address_depart_id
                record.return_address_id = record.employee_id.of_address_retour_id

    def _compute_markers_to_preview(self):
        """This is to display the markers of the start and end address of the tour on the map
        """
        for tour in self:
            date_preview = \
                tour.date and fields.Datetime.from_string(tour.date).strftime('%Y-%m-%d 00:00:00') or False
            default_marker = {
                'id': tour.id * -1,  # Negative id to avoid conflict with real interventions on the map
                'last_address_tour': False,
                'tour_number': False,
                'partner_phone': False,
                'partner_mobile': False,
                'date': date_preview,
                'rendered': True
            }
            same_start_return_address = tour.start_address_id.geo_lng == tour.return_address_id.geo_lng and \
                tour.start_address_id.geo_lat == tour.return_address_id.geo_lat
            # Start of the tour
            start_marker = default_marker.copy()
            start_marker['map_color_tour'] = 'start'
            start_marker['iconUrl'] = 'black'
            start_marker['tache_name'] = u'Départ' if not same_start_return_address else u'Départ/Retour'
            start_marker['address_city'] = tour.start_address_id.city
            start_marker['partner_name'] = tour.start_address_id.name
            start_marker['geo_lng'] = tour.start_address_id.geo_lng
            start_marker['geo_lat'] = tour.start_address_id.geo_lat
            start_marker['address_zip'] = tour.start_address_id.zip
            # End of the tour
            end_marker = default_marker.copy()
            end_marker['id'] -= 1  # Remove one to get another id to avoid conflict with the start marker id on the map
            end_marker['map_color_tour'] = 'stop'
            end_marker['iconUrl'] = 'black'
            end_marker['tache_name'] = u'Retour' if not same_start_return_address else u'Départ/Retour'
            end_marker['address_city'] = tour.return_address_id.city
            end_marker['partner_name'] = tour.return_address_id.name
            end_marker['geo_lng'] = tour.return_address_id.geo_lng
            end_marker['geo_lat'] = tour.return_address_id.geo_lat
            end_marker['address_zip'] = tour.return_address_id.zip
            tour.markers_to_preview = json.dumps([start_marker, end_marker])

    @api.multi
    def _set_start_address_id(self):
        # allow to set start_address_id from the form view if we want to change the default address
        pass

    @api.multi
    def _set_return_address_id(self):
        # allow to set return_address_id from the form view if we want to change the default address
        pass

    @api.multi
    @api.depends('employee_id', 'date', 'is_bloque', 'employee_id.of_tz', 'employee_id.of_tz_offset')
    def _compute_is_complet(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        intervention_obj = self.env['of.planning.intervention']
        today_str = fields.Date.today()
        for tournee in self:
            if tournee.is_bloque:
                tournee.is_complet = False
                continue
            if tournee.date < today_str:
                tournee.is_complet = True
                continue
            employee = tournee.employee_id
            if employee.of_tz and employee.of_tz != 'Europe/Paris':
                self = self.with_context(tz=employee.of_tz)

            interventions = intervention_obj.search([
                ('employee_ids', 'in', employee.id),
                ('date', '<=', tournee.date),
                ('date_deadline', '>=', tournee.date),
                ('state', 'in', ('draft', 'confirm'))
            ], order="date")
            if not interventions:
                tournee.is_complet = False
                continue

            date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(tournee.date))
            horaires_emp = employee.get_horaires_date(tournee.date)[employee.id]
            nb_creneaux = len(horaires_emp)
            if nb_creneaux == 0:
                tournee.is_complet = True
                continue
            start_end_list = [(0, horaires_emp[0][0])]  # liste des créneaux non-travaillés de l'employé
            start_end_list.extend((horaires_emp[i - 1][1], horaires_emp[i][0]) for i in range(1, nb_creneaux))
            start_end_list.append((horaires_emp[-1][1], 24))
            debut_journee = horaires_emp[0][0]
            fin_journee = horaires_emp[-1][1]

            for intervention in interventions:
                start_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date))
                if start_local.day != date_local.day:
                    start_flo = debut_journee
                else:
                    start_flo = (start_local.hour +
                                 start_local.minute / 60 +
                                 start_local.second / 3600)

                end_local = fields.Datetime.context_timestamp(
                    self, fields.Datetime.from_string(intervention.date_deadline))
                if end_local.day != date_local.day:
                    end_flo = fin_journee
                else:
                    end_flo = (end_local.hour +
                               end_local.minute / 60 +
                               end_local.second / 3600)

                start_end_list.append((start_flo, end_flo))
            start_end_list.sort()

            is_complet = True
            last_end = 0
            for s, e in start_end_list:
                if s - last_end > 0:
                    is_complet = False
                    break
                if e > last_end:
                    last_end = e
            tournee.is_complet = is_complet

    @api.multi
    @api.depends('tour_line_ids')
    def _compute_max_line_sequence(self):
        for tour in self:
            tour.max_line_sequence = (
                max(tour.mapped('tour_line_ids.sequence') or [0]) + 1)

    @api.multi
    def _reset_sequence(self):
        for tour in self:
            current_sequence = 1
            for line in tour.tour_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    @api.onchange('zip_id')
    def _onchange_zip_id(self):
        if self.zip_id:
            self.epi_lat = self.zip_id.geo_lat
            self.epi_lon = self.zip_id.geo_lng

    def _send_osrm_trip_request(self):
        """Start a trip request to the OSRM server.
        The trip plugin solves the Traveling Salesman Problem using a greedy heuristic (farthest-insertion algorithm).
        The returned path does not have to be the fastest path, as TSP is NP-hard it is only an approximation.

        In our case some Tour should not have the same start and end point on the day.
        So we will always send the start point and all points for the interventions on the day to get the best path
        given by the OSRM server, and we will add the end point at the end of the path.

        Exemple:
        * Start point and end point are the same : A
            - Interventions: B, C, D, E
            - Points sent to OSRM: A, B, C, D, E.
        The OSRM server will return a path like: B, C, A, D, E. So we can easily take the path at the start point and
        follow the order of the path to visit all interventions.
        "B, C, A, D, E" become "A, D, E, B, C".

        * Start point and end point are different : A, F
            - Interventions: B, C, D, E
            - Points sent to OSRM: A, B, C, D, E.
        The OSRM server will return a path like: B, C, A, D, E. And we will add F at the end of the path.
        "B, C, A, D, E" become "B, C, A, D, E, F".
        """
        self.ensure_one()

        routing_base_url = config.get('of_routing_base_url', '')
        routing_version = config.get('of_routing_version', '')
        routing_profile = config.get('of_routing_profile', '')
        if not (routing_base_url and routing_version and routing_profile):
            return {}

        # start points
        start_address = self.start_address_id
        if not start_address:
            start_address = self.employee_id.start_address_id
        # end points
        stop_address = self.return_address_id
        if not stop_address:
            stop_address = self.employee_id.return_address_id
        
        osrm_url = '%strip/%s/%s/' % (routing_base_url, routing_version, routing_profile)
        
        coords_str = "%s,%s" % (start_address.geo_lng, start_address.geo_lat)
        # get intervention points from the tour lines
        interventions_coordinates = {}
        coordinates_interventions = {}
        for line in self.tour_line_ids:
            interventions_coordinates[line.intervention_id.id] = "%s,%s" % (
                line.intervention_id.geo_lng, line.intervention_id.geo_lat)
            coordinates_interventions[interventions_coordinates[line.intervention_id.id]] = line.intervention_id.id
            coords_str += ";%s,%s" % (line.geo_lng, line.geo_lat)
        
        # request
        full_query = osrm_url + coords_str
        full_query += '?overview=false'
        try:
            print "OSRM request: %s" % full_query
            req = requests.get(full_query, timeout=10)
            res = req.json()
        except Exception:
            res = {}
        print "------------------------------------"
        print "interventions_coordinates = %s" % interventions_coordinates
        print "coordinates_interventions = %s" % coordinates_interventions
        for trip in res.get('trips', []):
            print trip
        return res

    @api.multi
    def _prepare_tour_line(self, idx, intervention):
        self.ensure_one()
        intervention = intervention.with_context(active_tour_id=self.id)
        geo_lat = intervention.geo_lat
        geo_lng = intervention.geo_lng
        if not geo_lat or not geo_lng:
            geo_lat = self.employee_id.of_address_depart_id.geo_lat
            geo_lng = self.employee_id.of_address_depart_id.geo_lng
        city = intervention.address_city
        if not city:
            city = self.employee_id.of_address_depart_id.city
        address_city = city
        return {
            'sequence': idx,
            'tour_id': self.id,
            'intervention_id': intervention.id,
            'geo_lat': geo_lat,
            'geo_lng': geo_lng,
            'city': city,
            'address_city': address_city,
        }

    @api.multi
    def action_compute_osrm_steps(self):
        for tour in self:
            if not tour.tour_line_ids:
                tour.update_tour_lines()
            for line in tour.tour_line_ids:
                line._get_osrm_steps()

    @api.multi
    def action_set_tour_as_full(self):
        """ Set the state of the tour as full if is flagged as 'complete' and if the tour'state is 'draft'."""
        tours = self.filtered(lambda t: t.is_complet and t.state == 'draft')
        tours and tours.write({'state': 'full'})

    @api.multi
    def action_optimize_tour(self):
        self.ensure_one()
        view = self.env.ref('of_planning_tournee.tour_planning_optimization_wizard_view_form')
        context = self._context.copy()
        context.update({'default_tour_id': self.id})
        return {
            'name': _('Optimize tour'),
            'type': 'ir.actions.act_window',
            'res_model': 'tour.planning.optimization.wizard',
            'view_mode': 'form',
            'view_id': view.id,
            'domain': [],
            'target': 'new',
            'context': context
        }

    @api.multi
    def update_tour_lines(self):
        for tour in self:
            tour.tour_line_ids.unlink()
            lines = [
                (0, 0, tour._prepare_tour_line(idx, intervention))
                for idx, intervention in enumerate(tour.intervention_ids, 1)]
            tour.with_context(tour_create=True).write({'tour_line_ids': lines})

    @api.model
    def get_color_map(self):
        if self._context.get('active_tour_id'):
            title = ""
            # gold is easier to read than yellow on the legend with a white background
            v0 = {'label': u"Départ", 'value': 'gold'}
            v1 = {'label': u'Intervention', 'value': 'blue'}
            v2 = {'label': u'Arrivée', 'value': 'red'}
            return {"title": title, "values": (v0, v1, v2)}
        return None

    @api.model
    def create(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        # @todo: vérifier pertinence du champ is_bloque avec aymeric
        if vals.get('is_bloque'):
            if intervention_obj.search([('date', '>=', vals['date']), ('date', '<=', vals['date']),
                                        ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                        ('employee_ids', 'in', vals['employee_id'])]):
                raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')
        return super(OFPlanningTournee, self).create(vals)

    @api.multi
    def write(self, vals):
        intervention_obj = self.env['of.planning.intervention']
        if vals.get('tour_line_ids'):
            current_sequence = {}
            for tour in self:
                current_sequence[tour.id] = {}
                for tour_line in tour.tour_line_ids:
                    current_sequence[tour.id][tour_line.id] = tour_line.sequence
        for tournee in self:
            if vals.get('is_bloque', tournee.is_bloque):
                date_intervention = vals.get('date', tournee.date)
                employee_id = vals.get('employee_id', tournee.employee_id.id)
                if intervention_obj.search([('date', '>=', date_intervention), ('date', '<=', date_intervention),
                                            ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                            ('employee_ids', 'in', employee_id)]):
                    raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')
        result = super(OFPlanningTournee, self).write(vals)
        self._reset_sequence()
        for tour in self:
            print "before ", current_sequence[tour.id]
            print "after ", {tour_line.id: tour_line.sequence for tour_line in tour.tour_line_ids}
        return result

    @api.multi
    def _write(self, values):
        res = super(OFPlanningTournee, self)._write(values)
        # Low level implementation to ensure that we will update the state of the tour after the computed fields.
        self.action_set_tour_as_full()
        return res


class OFPlanningTourneeLine(models.Model):
    _name = 'of.planning.tour.line'
    _description = 'Tour lines'
    _order = 'tour_id, sequence asc'

    sequence = fields.Integer(string=u"Séquence", required=True, default=1, copy=False, index=True)
    tour_id = fields.Many2one(comodel_name='of.planning.tournee', string='Tour', required=True, ondelete='cascade')
    intervention_id = fields.Many2one(
        comodel_name='of.planning.intervention', string='Intervention', required=True, ondelete='cascade')
    geo_lat = fields.Float(string='Latitude', readonly=True)
    geo_lng = fields.Float(string='Longitude', readonly=True)
    city = fields.Char(string='City', readonly=True)
    address_city = fields.Char(string="Ville", readonly=True)
    previous_geo_lat = fields.Float(string='Latitude of the previous point', compute='_compute_line_data')
    previous_geo_lng = fields.Float(string='Longitude of the previous point', compute='_compute_line_data')
    next_geo_lat = fields.Float(string='Latitude of the next point', compute='_compute_line_data')
    next_geo_lng = fields.Float(string='Longitude of the next point', compute='_compute_line_data')
    is_first_line_of_tour = fields.Boolean(string='First line of the tour', compute='_compute_line_data')
    is_last_line_of_tour = fields.Boolean(string='Last line of the tour', compute='_compute_line_data')
    # Related fields from intervention
    date_start = fields.Datetime(
        related='intervention_id.date', string='Start date', readonly=True, store=True)
    employee_ids = fields.Many2many(related='intervention_id.employee_ids', string='Employees', readonly=True)
    duration = fields.Float(related='intervention_id.duree', string='Duration', readonly=True)
    tache_name = fields.Char(related='intervention_id.tache_id.name', readonly=True)
    partner_name = fields.Char(related='intervention_id.partner_id.name')
    address_zip = fields.Char(related='intervention_id.address_id.zip', readonly=True)
    partner_phone = fields.Char(related='intervention_id.partner_id.phone', readonly=True)
    partner_mobile = fields.Char(related='intervention_id.partner_id.mobile', readonly=True)
    map_color_tour = fields.Char(related='intervention_id.map_color_tour', string='Color')
    tour_number = fields.Char(related='intervention_id.tour_number', string='Tour number')
    # OSRM data for the map
    osrm_query = fields.Text(string='OSRM query')
    osrm_steps = fields.Text(string='OSRM steps')
    geojson_data = fields.Text(string='Geojson data')

    @api.multi
    def _compute_line_data(self):
        for line in self:
            print "line ", line
            print "line.sequence ", line.sequence
            # lines are sorted by dates (date_start)
            previous_line = self.search([('tour_id', '=', line.tour_id.id), ('sequence', '<', line.sequence)])
            next_line = self.search([('tour_id', '=', line.tour_id.id), ('sequence', '>', line.sequence)])
            print "previous_line ", previous_line
            print "next_line ", next_line
            is_first_line_of_tour = next_line != self.env[self._name]
            is_last_line_of_tour = not next_line
            if previous_line:
                print "previous_line[-1] ", previous_line[-1]
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
            print "previous_geo_lat ", previous_geo_lat
            print "previous_geo_lng ", previous_geo_lng
            print "next_geo_lat ", next_geo_lat
            print "next_geo_lng ", next_geo_lng
            print "is_first_line_of_tour ", is_first_line_of_tour
            print "is_last_line_of_tour ", is_last_line_of_tour
            line.previous_geo_lat = previous_geo_lat
            line.previous_geo_lng = previous_geo_lng
            line.next_geo_lat = next_geo_lat
            line.next_geo_lng = next_geo_lng
            line.is_first_line_of_tour = is_first_line_of_tour
            line.is_last_line_of_tour = is_last_line_of_tour

    def _get_osrm_steps(self):
        self.ensure_one()
        full_query = False
        steps = False
        geojson_data = False
        routing_base_url = config.get("of_routing_base_url", "")
        routing_version = config.get("of_routing_version", "")
        routing_profile = config.get("of_routing_profile", "")
        if not (routing_base_url and routing_version and routing_profile) or (
                not self.geo_lat or not self.geo_lng) or (not self.previous_geo_lat or not self.previous_geo_lng):
            return {}
        osrm_url = routing_base_url + "route/" + routing_version + "/" + routing_profile + "/"
        if not self.is_last_line_of_tour:
            coords_str = "%s,%s;%s,%s" % (self.previous_geo_lng, self.previous_geo_lat, self.geo_lng, self.geo_lat)
        else:
            coords_str = "%s,%s;%s,%s;%s,%s" % (
                self.previous_geo_lng, self.previous_geo_lat, self.geo_lng, self.geo_lat,
                self.next_geo_lng, self.next_geo_lat)
        # request
        full_query = osrm_url + coords_str + "?geometries=geojson&steps=true&overview=false"
        try:
            req = requests.get(full_query, timeout=10)
            res = req.json()
        except Exception:
            res = {}
        if res.get('routes'):
            route = res['routes'][0]
            legs = route['legs']
            steps = []
            # we should have 2 legs for the last line of the tour because there is the previous address and
            # the return address
            for leg in legs:
                steps += leg['steps']
            geojson_data = [step['geometry'] for step in steps]
            geojson_data = json.dumps(geojson_data)
        self.osrm_query = full_query
        self.osrm_steps = steps
        self.geojson_data = geojson_data

    @api.model
    def custom_get_color_map_with_preview(self):
        title = ""
        v0 = {'label': u"DI à planifier", 'value': 'green'}
        # gold is easier to read than yellow on the legend with a white background
        v1 = {'label': u'Intervention(s) de la tournée', 'value': 'blue'}
        return {"title": title, "values": (v0, v1)}

    @api.model
    def custom_get_color_map(self):
        title = ""
        # gold is easier to read than yellow on the legend with a white background
        v1 = {'label': u"Départ de la tournée", 'value': 'black'}
        v2 = {'label': u'Intervention(s)', 'value': 'blue'}
        v3 = {'label': u'Arrivée de la tournée', 'value': 'black'}
        return {"title": title, "values": (v1, v2, v3)}

    @api.model
    def create(self, values):
        line = super(OFPlanningTourneeLine, self).create(values)
        # We do not reset the sequence if we are copying a complete tour
        if not self.env.context.get('keep_line_sequence', False):
            line.tour_id._reset_sequence()
        return line

    def write(self, vals):
        return super(OFPlanningTourneeLine, self).write(vals)
