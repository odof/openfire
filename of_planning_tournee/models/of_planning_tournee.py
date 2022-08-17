# -*- coding: utf-8 -*-
import json
import requests
from odoo import api, models, fields
from odoo.exceptions import ValidationError
from odoo.tools import config


class OfPlanningTournee(models.Model):
    _name = "of.planning.tournee"
    _inherit = 'of.map.view.mixin'
    _description = u"Tournée"
    _order = 'date DESC'
    _rec_name = 'date'

    date = fields.Date(string='Date', required=True)
    date_jour = fields.Char(compute="_compute_date_jour", string="Jour")
    # Champ equipe_id avant la refonte du planning nov. 2019.
    # Conservé quelques jours pour la transtion des données.
    # À supprimer par la suite.
    equipe_id = fields.Many2one('of.planning.equipe', string=u'Équipe')
    employee_id = fields.Many2one('hr.employee', string=u'Intervenant', required=True, ondelete='cascade')
    employee_other_ids = fields.Many2many(
        'hr.employee', 'tournee_employee_other_rel', 'tournee_id', 'employee_id', string=u'Équipiers', required=True,
        domain="['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]")
    secteur_id = fields.Many2one('of.secteur', string='Secteur', domain="[('type', 'in', ['tech', 'tech_com'])]")
    epi_lat = fields.Float(string=u'Épicentre Lat', digits=(12, 12))
    epi_lon = fields.Float(string=u'Épicentre Lon', digits=(12, 12))
    address_depart_id = fields.Many2one('res.partner', string=u'Adresse départ')
    address_retour_id = fields.Many2one('res.partner', string='Adresse retour')

    zip_id = fields.Many2one('res.better.zip', 'Ville')
    distance = fields.Float(string='Eloignement (km)', digits=(12, 4), default=20.0)
    is_complet = fields.Boolean(compute="_compute_is_complet", string='Complet', store=True)
    is_bloque = fields.Boolean(string=u'Bloqué', help=u'Journée bloquée : ne sera pas proposée à la planification')
    is_confirme = fields.Boolean(
        string=u'Confirmé', default=True,
        help=u'Une tournée non confirmée sera supprimée si on lui retire ses rendez-vous')
    date_min = fields.Date(related="date", string="Date min")
    date_max = fields.Date(related="date", string="Date max")
    intervention_ids = fields.Many2many(
        'of.planning.intervention', 'of_planning_intervention_of_planning_tournee_rel', 'tournee_id', 'intervention_id',
        string='Interventions')
    intervention_map_ids = fields.One2many('of.planning.intervention', compute="_compute_intervention_map_ids")
    tour_line_ids = fields.One2many(
        comodel_name='of.planning.tournee.line', inverse_name='tour_id', string='Tour lines')
    map_tour_line_ids = fields.One2many(
        comodel_name='of.planning.tournee.line', inverse_name='tour_id', string='Tour lines')
    osrm_route_steps = fields.Text(string='OSRM route steps')

    _sql_constraints = [
        ('date_employee_uniq', 'unique (date,employee_id)',
         u"Il ne peut exister qu'une tournée par employé pour un jour donné")
    ]

    @api.depends('date')
    def _compute_date_jour(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for tournee in self:
            jour = ""
            if tournee.date:
                date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(tournee.date))
                jour = date_local.strftime("%A").capitalize()
            tournee.date_jour = jour

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

    @api.depends('intervention_ids')
    def _compute_intervention_map_ids(self):
        for tour in self:
            intervention_ids = [(6, 0, [inter.id for inter in tour.intervention_ids if inter.geo_lat != 0])]
            tour.intervention_map_ids = intervention_ids
        return True

    @api.onchange('zip_id')
    def _onchange_zip_id(self):
        if self.zip_id:
            self.epi_lat = self.zip_id.geo_lat
            self.epi_lon = self.zip_id.geo_lng

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.address_depart_id = self.employee_id.of_address_depart_id
            self.address_retour_id = self.employee_id.of_address_retour_id

    @api.onchange('address_depart_id')
    def _onchange_address_depart_id(self):
        if self.address_depart_id:
            self.address_retour_id = self.address_depart_id

    @api.model
    def create(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        # @todo: vérifier pertinence du champ is_bloque avec aymeric
        if vals.get('is_bloque'):
            if intervention_obj.search([('date', '>=', vals['date']), ('date', '<=', vals['date']),
                                        ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                        ('employee_ids', 'in', vals['employee_id'])]):
                raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')
        return super(OfPlanningTournee, self).create(vals)

    @api.multi
    def write(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        for tournee in self:
            if vals.get('is_bloque', tournee.is_bloque):
                date_intervention = vals.get('date', tournee.date)
                employee_id = vals.get('employee_id', tournee.employee_id.id)
                if intervention_obj.search([('date', '>=', date_intervention), ('date', '<=', date_intervention),
                                            ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                            ('employee_ids', 'in', employee_id)]):
                    raise ValidationError(u'Il existe déjà des interventions dans la journée pour cet intervenant.')
        return super(OfPlanningTournee, self).write(vals)

    def _send_osrm_request(self):
        routing_base_url = config.get("of_routing_base_url", "")
        routing_version = config.get("of_routing_version", "")
        routing_profile = config.get("of_routing_profile", "")
        if not (routing_base_url and routing_version and routing_profile):
            return {}
        osrm_url = routing_base_url + "route/" + routing_version + "/" + routing_profile + "/"
        # start points
        start_address = self.address_depart_id
        if not start_address:
            start_address = self.employee_id.of_address_depart_id
        coords_str = "%s,%s" % (start_address.geo_lng, start_address.geo_lat)
        # get intervention points from the tour lines
        for line in self.tour_line_ids:
            coords_str += ";%s,%s" % (line.geo_lng, line.geo_lat)
        # end points
        stop_address = self.address_retour_id
        if not stop_address:
            stop_address = self.employee_id.of_address_retour_id
        coords_str += ";%s,%s" % (stop_address.geo_lng, stop_address.geo_lat)
        # request
        full_query = osrm_url + coords_str + "?geometries=geojson&steps=true&overview=false"
        try:
            req = requests.get(full_query, timeout=10)
            res = req.json()
        except Exception:
            res = {}
        return res

    @api.multi
    def action_compute_osrm_steps(self):
        for tour in self:
            steps = []
            if not tour.intervention_map_ids:
                return steps
            if not tour.tour_line_ids:
                tour.update_tour_lines()
            for line in tour.tour_line_ids:
                line._get_osrm_steps()

    @api.multi
    def _prepare_tour_line(self, intervention):
        self.ensure_one()
        return {
            'tour_': self.id,
            'intervention_id': intervention.id,
        }

    @api.multi
    def update_tour_lines(self):
        for tour in self:
            tour.tour_line_ids.unlink()
            lines = [(0, 0, tour._prepare_tour_line(intervention)) for intervention in tour.intervention_ids]
            tour.write({'tour_line_ids': lines})

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


class OFPlanningTourneeLine(models.Model):
    _name = 'of.planning.tournee.line'
    _description = 'Tour lines'
    _order = 'tour_id, date_start'

    tour_id = fields.Many2one(comodel_name='of.planning.tournee', string='Tour', required=True, ondelete='cascade')
    intervention_id = fields.Many2one(
        comodel_name='of.planning.intervention', string='intervention', required=True, ondelete='cascade')
    osrm_steps = fields.Text('OSRM steps')
    geojson_data = fields.Text('Geojson data')
    # Related fields from intervention
    date_start = fields.Datetime(
        related='intervention_id.date', string='Start date', readonly=True, store=True)
    employee_ids = fields.Many2many(related='intervention_id.employee_ids', string='Employees', readonly=True)
    city = fields.Char(related='intervention_id.address_city', string='City', readonly=True)
    duration = fields.Float(related='intervention_id.duree', string='Duration', readonly=True)
    geo_lat = fields.Float(related='intervention_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='intervention_id.geo_lng', readonly=True)
    previous_geo_lat = fields.Float('Latitude of the previous point', compute='_compute_previous_coordinates')
    previous_geo_lng = fields.Float('Longitude of the previous point', compute='_compute_previous_coordinates')
    tache_name = fields.Char(related='intervention_id.tache_id.name', readonly=True)
    partner_name = fields.Char(related='intervention_id.partner_id.name')
    address_city = fields.Char(
        related='intervention_id.address_id.city', string="Ville", oldname="partner_city", readonly=True)
    address_zip = fields.Char(related='intervention_id.address_id.zip', readonly=True)
    partner_phone = fields.Char(related='intervention_id.partner_id.phone', readonly=True)
    partner_mobile = fields.Char(related='intervention_id.partner_id.mobile', readonly=True)
    map_color_tour = fields.Char(related='intervention_id.map_color_tour', string='Color')
    tour_number = fields.Char(related='intervention_id.tour_number', string='Tour number')
    first_address_tour = fields.Boolean(
        related='intervention_id.first_address_tour', string='Is the first address of the Tour ?')
    last_address_tour = fields.Boolean(
        related='intervention_id.last_address_tour', string='Is the last address of the Tour ?')

    @api.multi
    def _compute_previous_coordinates(self):
        for line in self:
            # lines are sorted by dates (date_start)
            previous_line = line.search([('tour_id', '=', line.tour_id.id), ('id', '<', line.id)], limit=1)
            if previous_line:
                geo_lat = previous_line.geo_lat
                geo_lng = previous_line.geo_lng
            else:
                geo_lat = False
                geo_lng = False
            line.previous_geo_lat = geo_lat
            line.previous_geo_lng = geo_lng

    def _get_osrm_steps(self):
        self.ensure_one()
        steps = False
        geojson_data = False
        routing_base_url = config.get("of_routing_base_url", "")
        routing_version = config.get("of_routing_version", "")
        routing_profile = config.get("of_routing_profile", "")
        if not (routing_base_url and routing_version and routing_profile) or (
                not self.geo_lat or not self.geo_lng) or (not self.previous_geo_lat or not self.previous_geo_lng):
            return {}
        osrm_url = routing_base_url + "route/" + routing_version + "/" + routing_profile + "/"
        coords_str = "%s,%s;%s,%s" % (self.previous_geo_lng, self.previous_geo_lat, self.geo_lng, self.geo_lat)
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
            steps = legs[0]['steps']
            geojson_data = [step['geometry'] for step in steps]
            geojson_data = json.dumps(geojson_data)
        self.osrm_steps = steps
        self.geojson_data = geojson_data
        return res

    @api.model
    def custom_get_color_map(self):
        title = ""
        # gold is easier to read than yellow on the legend with a white background
        v0 = {'label': u"Première intervention", 'value': 'gold'}
        v1 = {'label': u'Intervention(s)', 'value': 'blue'}
        v2 = {'label': u'Dernière intervention', 'value': 'red'}
        return {"title": title, "values": (v0, v1, v2)}
