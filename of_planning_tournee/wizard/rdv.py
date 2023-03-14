# -*- coding: utf-8 -*-

import json
import requests
import logging
import pytz
import urllib
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import config
from odoo.tools.float_utils import float_compare
from odoo.addons.of_planning_tournee.models.of_intervention_settings import SELECTION_SEARCH_TYPES
from odoo.addons.of_planning_tournee.models.of_intervention_settings import SELECTION_SEARCH_MODES
from odoo.addons.of_utils.models.of_utils import distance_points, hours_to_strs
from odoo.addons.calendar.models.calendar import calendar_id2real_id
from odoo.addons.of_planning_tournee.models.of_planning_tournee import WEEKDAYS_TR
from odoo.addons.of_planning_tournee.models.of_planning_tournee import AM_LIMIT_FLOAT

_logger = logging.getLogger(__name__)


"""
bug description quand changement de tache ou service lié puis changé?
# refonte employés et équipes: dans un premier temp, on limite la prise de rdv aux tache à 1 intervenant
"""


class OfTourneeRdv(models.TransientModel):
    _name = 'of.tournee.rdv'
    _description = u"Prise de RDV dans les tournées"

    @api.model
    def default_get(self, field_list=None):
        res = super(OfTourneeRdv, self).default_get(field_list)
        # Suivant que la prise de rdv se fait depuis la fiche client ou une demande d'intervention
        service_obj = self.env['of.service']
        partner_obj = self.env['res.partner']
        active_model = self._context.get('active_model', '')
        service = False
        partner = False
        address = False
        intervention = False
        if active_model == 'res.partner':
            partner_id = self._context['active_ids'][0]
            partner = partner_obj.browse(partner_id)
            service = service_obj.search([('partner_id', '=', partner.id), ('recurrence', '=', True)], limit=1)
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])
        elif active_model in ['of.service', 'of.planning.intervention']:
            active_record_id = self._context['active_ids'][0]
            active_record = self.env[active_model].browse(active_record_id)
            partner = active_record.partner_id
            address = active_record.address_id
            if active_model == 'of.service':
                service = active_record
            else:
                intervention = active_record
                service = intervention.service_id
            res['pre_employee_ids'] = [(6, 0, [emp.id for emp in active_record.employee_ids])]
        elif active_model == 'sale.order':
            order_id = self._context['active_ids'][0]
            order = self.env['sale.order'].browse(order_id)
            partner = order.partner_id
            service = service_obj.search([('order_id', '=', order_id)], limit=1)
            if not service:
                service = service_obj.search([('partner_id', '=', partner.id)], limit=1)
            address = order.partner_shipping_id or order.partner_id
        elif self._context.get('of_default_partner_id'):
            active_model = 'res.partner'
            partner_id = self._context.get('of_default_partner_id')
            partner = partner_obj.browse(partner_id)
            service = service_obj.search([('partner_id', '=', partner.id), ('recurrence', '=', True)], limit=1)
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])

        if address and not address.geo_lat and not address.geo_lng:
            address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
                                          '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)],
                                         limit=1) or address

        res['source_model'] = active_model
        res['partner_id'] = partner and partner.id or False
        res['partner_address_id'] = address and address.id or False
        res['service_id'] = service and service.id or False
        res['origin_intervention_id'] = intervention and intervention.id or False
        if service:
            res['day_ids'] = [(6, 0, service.jour_ids.ids)]
        if intervention:
            res['date_recherche_debut'] = fields.Date.today()
        elif service and service.date_next and service.date_next >= date.today().strftime(DEFAULT_SERVER_DATE_FORMAT):
            res['date_recherche_debut'] = service.date_next
            res['date_recherche_fin'] = service.date_fin
        return res

    @api.model
    def _default_day_ids(self):
        # added sudo() to avoid access rights issues from the website (no access for of.planning.tournee)
        days = self.env['of.jours'].sudo().search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        return [day.id for day in days]

    @api.model
    def _default_company(self):
        if self.env['ir.values'].get_default('of.intervention.settings', 'company_choice') == 'user':
            return self.env['res.company']._company_default_get('of.tournee.rdv')
        return False

    @api.model
    def _default_search_mode(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'search_mode') or 'oneway_or_return'

    @api.model
    def _default_search_type(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'search_type') or 'distance'

    @api.model
    def _default_slots_display_mode(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'slots_display_mode') or 'list'

    @api.model
    def _default_show_next_available_time_slots(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'show_next_available_time_slots')

    @api.model
    def _default_planning_task(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'default_planning_task_id')

    source_model = fields.Char(string="Source Model", readonly=True)
    slots_display_mode = fields.Char(
        string="Display mode", readonly=True, required=True, default=lambda s: s._default_slots_display_mode())
    show_next_available_time_slots = fields.Boolean(
        string="Display next time slots by date", readonly=True,
        default=lambda s: s._default_show_next_available_time_slots())
    # Champs de recherche
    partner_id = fields.Many2one(
        'res.partner', string="Client", required=True, readonly=True)
    partner_address_id = fields.Many2one(
        'res.partner', string="Adresse d'intervention", required=True,
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    geo_lat = fields.Float(related='partner_address_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='partner_address_id.geo_lng', readonly=True)
    precision = fields.Selection(related='partner_address_id.precision', readonly=True)
    ignorer_geo = fields.Boolean(u"Ignorer données géographiques")
    partner_address_street = fields.Char(related="partner_address_id.street", readonly=True)
    partner_address_street2 = fields.Char(related="partner_address_id.street2", readonly=True)
    partner_address_city = fields.Char(related="partner_address_id.city", readonly=True)
    partner_address_state_id = fields.Many2one(related="partner_address_id.state_id", readonly=True)
    partner_address_zip = fields.Char(related="partner_address_id.zip", readonly=True)
    partner_address_country_id = fields.Many2one(related="partner_address_id.country_id", readonly=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string=u"Magasin", required=True, default=lambda s: s._default_company())
    service_id = fields.Many2one(
        comodel_name='of.service', string=u"Demande d'intervention", domain="[('partner_id', '=', partner_id)]")
    origin_intervention_id = fields.Many2one(comodel_name='of.planning.intervention', string="Origin intervention")
    tache_id = fields.Many2one(
        comodel_name='of.planning.tache', string=u"Tâche", required=True, default=lambda s: s._default_planning_task())
    template_id = fields.Many2one(comodel_name='of.planning.intervention.template', string="Intervention template")
    creer_recurrence = fields.Boolean(
        string=u"Créer récurrence?",
        help=u"Créera une intervention récurrente s'il n'en existe pas déjà une associée à ce RDV.")
    duree = fields.Float(string=u'Durée', required=True, digits=(12, 5))
    pre_employee_ids = fields.Many2many(
        comodel_name='hr.employee', string=u"Intervenant(s)",
        domain="['|', ('of_tache_ids', 'in', tache_id), ('of_toutes_taches', '=', True)]",
        help=u"Pré-sélection des intervenants")
    date_recherche_debut = fields.Date(
        string=u"À partir du", required=True,
        default=lambda *a: (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'))
    date_recherche_fin = fields.Date(
        string="Jusqu'au", required=True, default=lambda *a: (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'))
    search_type = fields.Selection(
        selection=SELECTION_SEARCH_TYPES, string="Search type", required=True,
        default=lambda s: s._default_search_type())
    search_mode = fields.Selection(
        selection=SELECTION_SEARCH_MODES, string="Search mode", required=True,
        default=lambda s: s._default_search_mode())
    search_period_in_days = fields.Integer(string="Search period (in days)", default=7, required=True)
    day_ids = fields.Many2many(
        comodel_name='of.jours', relation='wizard_plan_intervention_days_rel', column1='wizard_id',
        column2='jour_id', string="Days", required=True, default=lambda s: s._default_day_ids())
    orthodromique = fields.Boolean(string=u"Distances à vol d'oiseau")

    # Champs de résultat
    display_res = fields.Boolean(string=u"Voir Résultats", default=False)  # Utilisé pour attrs invisible des résultats
    zero_result = fields.Boolean(string="Recherche infructueuse", default=False, help=u"Aucun résultat")
    can_show_more = fields.Boolean(string="Can show more", compute='_compute_can_show_more')
    planning_ids = fields.One2many(
        comodel_name='of.tournee.rdv.line', inverse_name='wizard_id', string=u"Proposition de RDVs")
    by_distance_planning_tree_ids = fields.One2many(
        comodel_name='of.tournee.rdv.line', compute='_compute_by_distance_planning_tree_ids',
        string="Slots by distance")
    by_duration_planning_tree_ids = fields.One2many(
        comodel_name='of.tournee.rdv.line', compute='_compute_by_duration_planning_tree_ids',
        string="Slots by duration")
    by_date_planning_tree_ids = fields.One2many(
        comodel_name='of.tournee.rdv.line', compute='_compute_by_date_planning_tree_ids',
        string="Slots by date")
    res_line_id = fields.Many2one(comodel_name='of.tournee.rdv.line', string=u"Créneau Sélectionné")
    map_line_id = fields.Many2one(comodel_name='of.tournee.rdv.line', string="Line selected for the map preview")
    map_tour_id = fields.Many2one(comodel_name='of.planning.tournee', string="Tour")
    additional_records = fields.Char(
        string="Data for displaying additional records", compute='_compute_additional_records')
    additional_record_geojson_data = fields.Text(
        string="Geojson data",
        help="Geojson data used to draw the route on the map between the meeting we are trying to plan and "
        "the previous/next coordinates")
    map_description_html = fields.Html(string="Map description", compute='_compute_intervention_map_data')
    map_tour_line_ids = fields.One2many(
        comodel_name='of.planning.tour.line', related='map_tour_id.tour_line_ids', string="Tour lines")

    name = fields.Char(string=u"Libellé", size=64, required=False)
    description = fields.Text(string="Description")
    employee_id = fields.Many2one(comodel_name='hr.employee', string=u"Intervenant")
    date_propos = fields.Datetime(string=u"RDV Début")
    date_propos_hour = fields.Float(string=u"Heure de début", digits=(12, 5))
    date_display = fields.Char(string="Jour du RDV", size=64, readonly=True)

    # champs pour la création ou mise à jour d'interventions récurrentes
    date_next = fields.Date(
        string=u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention")
    date_fin_planif = fields.Date(
        string=u'expiration de prochaine planif', help=u"Date à partir de laquelle l'intervention devient en retard")
    flexible = fields.Boolean(
        string="Inclure les RDV flexibles", help=u"Afficher les créneaux des RDV flexibles comme étant libre")

    @api.constrains('search_period_in_days')
    def _check_search_period_in_days(self):
        if self.search_period_in_days < 1 or self.search_period_in_days > 45:
            raise ValidationError(_("The value of 'Search period (in days)' must be between 1 and 45"))

    def _get_search_max_value(self):
        return self.env['ir.values'].get_default('of.intervention.settings', 'number_of_results') or 30

    @api.multi
    def _get_wizard_form_view_id(self):
        """Returns the right xml_id for the wizard form view depending on settings and search criteria.

        If display_mode is 'list', first tab should be the one with time slots lists and tour map.
        Second tab then is the one with calendar view.
        If display_mode is 'calendar', calendar view tab should be in first position.

        If in settings, option 'show_next_available_time_slots' is set to True, a second time slots list
        should go next to the first one.
        This second time slot list displays time slots ordered by date instead of proximity."""
        self.ensure_one()
        display_mode = self._default_slots_display_mode()
        # simple form view is for when we come from 'of.service' model, complete form view is for other source models
        if self.source_model in ['of.service', 'of.planning.intervention']:
            return self._get_wizard_list_mode_form_view_id() if display_mode == 'list' else \
                self._get_wizard_calendar_1st_mode_form_view_id()
        elif display_mode == 'list':
            return self._get_wizard_list_mode_complete_form_view_id()
        else:
            return self._get_wizard_calendar_1st_mode_complete_form_view_id()

    @api.multi
    def _get_wizard_list_mode_form_view_id(self):
        """Get the correct form view id for the wizard in list mode.
        """
        self.ensure_one()
        if self.show_next_available_time_slots:
            # Display both time slot lists
            return self.env.ref('of_planning_tournee.view_rdv_intervention_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref('of_planning_tournee.view_rdv_intervention_by_duration_wizard').id
        else:
            # Only display time slot list ordered by proximity
            return self.env.ref('of_planning_tournee.view_rdv_intervention_wo_date_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref('of_planning_tournee.view_rdv_intervention_by_duration_wo_date_wizard').id

    @api.multi
    def _get_wizard_calendar_1st_mode_form_view_id(self):
        """Get the correct form view id for the wizard in calendar 1st mode.
        """
        self.ensure_one()
        if self.show_next_available_time_slots:
            # Display calendar tab in first position, then time slots tab with both time slot lists
            return self.env.ref('of_planning_tournee.view_rdv_intervention_calendar_1st_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref('of_planning_tournee.view_rdv_intervention_calendar_1st_by_duration_wizard').id
        else:
            # Display calendar tab in first position, then time slots tab without time slot list ordered by date
            return self.env.ref(
                'of_planning_tournee.view_rdv_intervention_calendar_1st_wo_date_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref('of_planning_tournee.view_rdv_intervention_calendar_1st_by_duration_wo_date_wizard').id

    @api.multi
    def _get_wizard_list_mode_complete_form_view_id(self):
        """Get the correct complete form view id for the wizard in list mode.
        """
        self.ensure_one()
        if self.show_next_available_time_slots:
            # Display both time slot lists
            return self.env.ref('of_planning_tournee.view_rdv_intervention_complete_form_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref('of_planning_tournee.view_rdv_intervention_complete_form_by_duration_wizard').id
        else:
            # Only display time slot list ordered by proximity
            return self.env.ref(
                'of_planning_tournee.view_rdv_intervention_complete_wo_date_form_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref('of_planning_tournee.view_rdv_intervention_complete_form_by_duration_wo_date_wizard').id

    @api.multi
    def _get_wizard_calendar_1st_mode_complete_form_view_id(self):
        """Get the correct complete form view id for the wizard in calendar 1st mode.
        """
        self.ensure_one()
        if self.show_next_available_time_slots:
            # Display both time slot lists
            return self.env.ref(
                'of_planning_tournee.view_rdv_intervention_complete_form_calendar_1st_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref(
                    'of_planning_tournee.view_rdv_intervention_complete_form_calendar_1st_by_duration_wizard').id
        else:
            # Only display time slot list ordered by proximity
            return self.env.ref(
                'of_planning_tournee.view_rdv_intervention_complete_form_calendar_1st_wo_date_wizard').id \
                if self.search_type == 'distance' else \
                self.env.ref(
                'of_planning_tournee.view_rdv_intervention_complete_form_calendar_1st_by_duration_wo_date_wizard').id

    def _get_hidden_lines(self, search_str=None):
        if search_str is None:
            search_str = 'distance_utile, debut_dt, employee_id' if self.search_type == 'distance' \
                else 'duree_utile, debut_dt, employee_id'

        lines_hidden = self.env['of.tournee.rdv.line'].search([
            ('wizard_id', '=', self.id),
            ('disponible', '=', True),
            ('allday', '=', False),
            ('intervention_id', '=', False),
            '|',
            ('by_date_hidden', '=', True),
            '|',
            ('by_distance_hidden', '=', True),
            ('by_duration_hidden', '=', True),
        ], order=search_str)
        by_date_lines_hidden = lines_hidden.filtered(lambda l: l.by_date_hidden)
        by_distance_lines_hidden = lines_hidden.filtered(lambda l: l.by_distance_hidden)
        by_duration_lines_hidden = lines_hidden.filtered(lambda l: l.by_duration_hidden)
        return by_date_lines_hidden, by_distance_lines_hidden, by_duration_lines_hidden

    # @api.depends
    @api.multi
    def _compute_by_distance_planning_tree_ids(self):
        for wizard in self:
            lines = wizard.planning_ids.filtered(
                lambda l: not l.intervention_id and not l.allday and not l.by_distance_hidden)
            wizard.by_distance_planning_tree_ids = lines.sorted(
                key=lambda l: (l.distance_utile, l.debut_dt, l.employee_id))

    @api.multi
    def _compute_by_duration_planning_tree_ids(self):
        for wizard in self:
            lines = wizard.planning_ids.filtered(
                lambda l: not l.intervention_id and not l.allday and not l.by_duration_hidden)
            wizard.by_duration_planning_tree_ids = lines.sorted(
                key=lambda l: (l.duree_utile, l.debut_dt, l.employee_id))

    @api.multi
    def _compute_by_date_planning_tree_ids(self):
        for wizard in self:
            lines = wizard.planning_ids.filtered(
                lambda l: not l.intervention_id and not l.allday and not l.by_date_hidden)
            wizard.by_date_planning_tree_ids = lines.sorted(
                key=lambda l: (l.date, l.date_flo, l.employee_id))

    @api.depends('partner_address_id', 'partner_address_id.geocoding', 'partner_address_id.precision')
    def _compute_geocode_retry(self):
        geocodeur = self.env['ir.config_parameter'].get_param('geocoder_by_default')
        for wizard in self:
            address_id = wizard.partner_address_id
            if address_id.geocodeur != geocodeur:
                wizard.geocode_retry = False
            elif address_id.precision == 'not_tried' or address_id.geocoding == 'not_tried':
                wizard.geocode_retry = False
            else:
                wizard.geocode_retry = True

    def _compute_can_show_more(self):
        for wizard in self:
            by_date_lines_hidden, by_distance_lines_hidden, by_duration_lines_hidden = wizard._get_hidden_lines()
            wizard.can_show_more = bool(by_date_lines_hidden or by_distance_lines_hidden or by_duration_lines_hidden)

    @api.depends(
        'geo_lat', 'geo_lng', 'service_id', 'service_id.geo_lat', 'service_id.geo_lng', 'origin_intervention_id',
        'origin_intervention_id.geo_lat', 'origin_intervention_id.geo_lng')
    def _compute_additional_records(self):
        """Builds a list of dict to display additional records on the map, containing information about the field
        operation to be planned.
        """
        for wizard in self:
            additionnal_record = wizard.service_id or wizard.origin_intervention_id
            if not additionnal_record:
                wizard.additional_record = json.dumps({})
                continue

            records = []
            if wizard.map_tour_id:
                start_marker, end_marker = wizard.map_tour_id._get_start_stop_markers_data_for_tour()
                records.extend([start_marker, end_marker])

            date_preview = \
                wizard.map_line_id.debut_dt and \
                fields.Datetime.from_string(wizard.map_line_id.debut_dt).strftime('%Y-%m-%d %H:%M:%S') or False
            records.append({
                'id': additionnal_record.id * -1,  # Negative id to avoid conflict with real interventions on the map
                'map_color_tour': 'green',
                'iconUrl': 'green',
                'address_city': wizard.partner_address_city,
                'partner_name': wizard.partner_id.name,
                'tour_number': False,
                'geo_lng': wizard.geo_lng,
                'partner_phone': False,
                'geo_lat': wizard.geo_lat,
                'partner_mobile': False,
                'tache_name': wizard.tache_id.name,
                'date': date_preview,
                'address_zip': wizard.partner_address_zip,
                'rendered': True
            })
            wizard.additional_records = json.dumps(records)

    @api.depends('res_line_id', 'map_tour_id', 'map_line_id')
    def _compute_intervention_map_data(self):
        lang = self.env['res.lang']._lang_get(self.env.user.lang or 'fr_FR')
        date_format = lang and lang.date_format or DEFAULT_SERVER_DATE_FORMAT
        for wizard in self:
            tour = wizard.map_tour_id
            map_description_html = False
            if wizard.map_line_id:
                line_date = fields.Date.from_string(wizard.map_line_id.date).strftime(date_format)
                line_day = wizard.map_line_id.weekday
                line_day_str = '%s %s' % (line_day, line_date)
                line_employee = wizard.map_line_id.employee_id
                color = 'color: orange;' if wizard.res_line_id != wizard.map_line_id else ''
                map_description_html = _(
                    "<span style=\"font-size: x-small;font-weight: bold;%s\">Tour of %s, on %s</span>") % (
                        color, line_employee.name, line_day_str)
            wizard.map_description_html = map_description_html
            wizard.map_tour_line_ids = tour.map_tour_line_ids if tour else []

    # @api.onchange
    @api.onchange('search_period_in_days')
    def _onchange_search_period_in_days(self):
        self.ensure_one()
        if self.search_period_in_days:
            date_deb = fields.Date.from_string(self.date_recherche_debut)
            # Sub 1 day because the search period is inclusive
            date_fin = date_deb + timedelta(days=self.search_period_in_days - 1)
            self.date_recherche_fin = fields.Date.to_string(date_fin)

    @api.onchange('partner_address_id')
    def _onchange_partner_address_id(self):
        if self.partner_address_id:
            # Pour les objets du planning, le choix de la société se fait par un paramètre de config
            company_choice = self.env['ir.values'].get_default(
                'of.intervention.settings', 'company_choice') or 'contact'
            if company_choice == 'contact' and self.partner_address_id.company_id:
                self.company_id = self.partner_address_id.company_id.id
            elif company_choice == 'contact' and self.partner_id and self.partner_id.company_id:
                self.company_id = self.partner_id.company_id.id
            # en mode contact avec un contact sans société, ou en mode user
            else:
                self.company_id = self.env.user.company_id.id

    @api.onchange('service_id')
    def _onchange_service(self):
        """Affecte la tâche, la description et l'adresse"""
        if not self.service_id or self.origin_intervention_id:
            return

        service = self.service_id
        notes = [service.tache_id.name]
        if service.note:
            notes.append(service.note)

        vals = {
            'description': "\n".join(notes),
            'tache_id': service.tache_id,
            'partner_address_id': service.address_id,
            'template_id': service.template_id.id
        }
        self.update(vals)

    @api.onchange('origin_intervention_id')
    def _onchange_origin_intervention_id(self):
        if not self.origin_intervention_id:
            return

        intervention = self.origin_intervention_id
        vals = {
            'description': intervention.description,
            'tache_id': intervention.tache_id,
            'partner_address_id': intervention.address_id,
            'service_id': intervention.service_id,
        }
        self.update(vals)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if not self.template_id:
            return
        template = self.template_id
        self.update({'tache_id': template.tache_id})

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        """Affecte creer_recurrence, duree et pre_employee_ids"""
        vals = {'service_id': False}
        if self.tache_id:
            service_obj = self.env['of.service']
            if self.service_id and self.service_id.tache_id.id == self.tache_id.id:
                del vals['service_id']
            else:
                service = service_obj.search([
                    ('partner_id', '=', self.partner_id.id), ('tache_id', '=', self.tache_id.id)], limit=1)
                if service:
                    vals['service_id'] = service

            if vals.get('service_id', self.service_id):
                vals['creer_recurrence'] = False
            else:
                # Si il n'y a pas d'a_programmer, on affecte creer_recurrence en fonction de la tâche
                vals['creer_recurrence'] = self.tache_id.recurrence

            # If the duration is not set, we set it to 1 hour by default to avoid an error when searching time slots
            if not self.duree:
                vals['duree'] = self.tache_id.duree or 1.0

            employees = [employee.id for employee in self.pre_employee_ids if employee in self.tache_id.employee_ids]
            vals['pre_employee_ids'] = employees
        self.update(vals)

    @api.onchange('date_recherche_debut')
    def _onchange_date_recherche_debut(self):
        """Affecte date_recherche_fin"""
        self.ensure_one()
        if self.date_recherche_debut:
            period_in_days = self.search_period_in_days or 7
            date_deb = fields.Date.from_string(self.date_recherche_debut)
            date_fin = date_deb + timedelta(days=period_in_days)
            self.date_recherche_fin = fields.Date.to_string(date_fin)

    @api.onchange('date_recherche_fin')
    def _onchange_date_recherche_fin(self):
        """Vérifie la cohérence des dates de recherche"""
        self.ensure_one()
        if self.date_recherche_fin and self.date_recherche_fin < self.date_recherche_debut:
            raise UserError(u"La date de fin de recherche doit être postérieure à la date de début de recherche")
        # Sub 1 day because the search period is inclusive
        start_date = fields.Date.from_string(self.date_recherche_debut) - timedelta(days=1)
        end_date = fields.Date.from_string(self.date_recherche_fin)
        self.search_period_in_days = (end_date - start_date).days

    @api.model
    def _get_additional_record_geojson_data(self, line):
        """ Get the additional geojson data for the current intervention we are planning which will be added to the
        tour route.
        That data will be used to display the route to go to the intervention on the map within the current tour route.
        """
        tour = line.tour_id
        previous_geo_lat = line.previous_geo_lat
        previous_geo_lng = line.previous_geo_lng
        next_geo_lat = line.next_geo_lat
        next_geo_lng = line.next_geo_lng
        if not tour or not previous_geo_lat or not previous_geo_lng or not next_geo_lat or not next_geo_lng:
            return False
        osrm_base_url = tour and tour._get_osrm_base_url() or False
        geojson_data = False
        coords_str = "%s,%s;%s,%s;%s,%s" % (
            line.previous_geo_lng, line.previous_geo_lat, line.wizard_id.geo_lng, line.wizard_id.geo_lat,
            line.next_geo_lng, line.next_geo_lat)
        full_query = '%s/%s?geometries=geojson&steps=true&overview=false' % (osrm_base_url, coords_str)
        steps, _null, _null = self.env['of.planning.tour.line']._get_osrm_steps_data(full_query)
        geojson_data = [step['geometry'] for step in steps]
        geojson_data = geojson_data and json.dumps(geojson_data)
        return geojson_data

    # Actions
    @api.multi
    def action_open_wizard(self):
        self.ensure_one()
        form_view_id = self._get_wizard_form_view_id()
        context = self._context.copy()
        return {
            'name': _("Plan intervention"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(form_view_id, 'form')],
            'res_model': 'of.tournee.rdv',
            'res_id': self.id,
            'target': 'new',
            'context': context
        }

    @api.multi
    def button_calcul(self):
        """
        Lance la recherche de créneaux dispos
        @todo: Remplacer le retour d'action par un return True, mais pour l'instant cela
          ne charge pas correctement la vue du planning.
        """
        self.ensure_one()
        # empty the current selected tour for the map
        if self.map_tour_id:
            self.map_tour_id = False
        # empty the current selected line for the map
        if self.map_line_id:
            self.map_line_id = False
        self.compute()
        context = dict(self._context, employee_domain=self._get_employee_possible())
        form_view_id = self._get_wizard_form_view_id()
        return {
            'name': _("Plan intervention"),
            'type': 'ir.actions.act_window',
            'res_model': 'of.tournee.rdv',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(form_view_id, 'form')],
            'res_id': self.id,
            'target': 'new',
            'context': context,
            'flags': {'initial_mode': 'edit', 'form': {'options': {'mode': 'edit'}}},
        }

    @api.multi
    def button_confirm(self):
        """
        Crée un RDV d'intervention puis l'ouvre en vue form.
        Crée aussi une intervention récurrente si besoin.
        """
        self.ensure_one()
        context = self._context.copy()
        group_flex = self.env.user.has_group('of_planning.of_group_planning_intervention_flexibility')
        if not context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        intervention_obj = self.env['of.planning.intervention']
        service_obj = self.env['of.service']

        # Vérifier que la date de début et la date de fin sont dans les créneaux
        employee = self.employee_id
        if not employee.of_segment_ids:
            raise UserError("Il faut configurer l'horaire de travail de tous les intervenants.")

        date_propos_dt = fields.Datetime.from_string(self.date_propos)  # datetime utc proposition de rdv

        values = self.get_values_intervention_create()

        intervention = intervention_obj.create(values)
        if group_flex:
            others = intervention.get_overlapping_intervention().filtered('flexible')
            if others:
                others.button_postponed()
        intervention.onchange_company_id()  # Permet de renseigner l'entrepôt
        # if we came from a postponed intervention, we want to keep the copied values of the original intervention
        if not self.origin_intervention_id:
            intervention.with_context(  # Charger les lignes de facturation
                of_import_service_lines=True)._onchange_service_id()
            intervention.with_context(of_import_service_lines=True)._onchange_tache_id()  # Load invoice lines
            # Load questionnary lines and more if coming from `res.partner` object
            intervention.with_context(
                of_intervention_wizard=True,
                of_from_contact_form=self.source_model == 'res.partner' and not self.service_id
            ).onchange_template_id()

        contract_custom = self.sudo().env['ir.module.module'].search([('name', '=', 'of_contract_custom')])
        # Creation/mise à jour du service si creer_recurrence
        if self.date_next:
            if self.service_id:
                self.service_id.write({
                    'date_next': self.date_next,
                    'date_fin': self.date_fin_planif
                })
            elif self.creer_recurrence and (not contract_custom or contract_custom.state != 'installed'):
                intervention.service_id = service_obj.create(self._get_service_data(date_propos_dt.month))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.planning.intervention',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': intervention.id,
            'target': 'current',
            'context': context,
            'flags': {'initial_mode': 'edit', 'form': {'options': {'mode': 'edit'}}},
        }

    def action_show_more_results(self):
        """Display more results in the tree views"""
        self.ensure_one()
        # number max of results to display
        number_of_results = self.env['ir.values'].get_default('of.intervention.settings', 'number_of_results')
        by_date_lines_hidden, by_distance_lines_hidden, by_duration_lines_hidden = self._get_hidden_lines()
        # update lines to hide the lines who are above the number_of_results
        by_date_lines_hidden[:number_of_results].write({'by_date_hidden': False})
        by_distance_lines_hidden[:number_of_results].write({'by_distance_hidden': False})
        by_duration_lines_hidden[:number_of_results].write({'by_duration_hidden': False})
        return self.action_open_wizard()

    # Autres

    @api.multi
    def _get_employee_possible(self):
        self.ensure_one()
        employee_ids = []
        for planning in self.planning_ids:
            if planning.employee_id.id not in employee_ids:
                employee_ids.append(planning.employee_id.id)
        return employee_ids

    @api.multi
    def compute(self, sudo=False, mode='new', secteur_id=False, web=False):
        u"""
        Remplit le champ planning_ids avec les créneaux non travaillés et les RDV tech.
        Lance le calcul des distances et sélectionne un résultat si il y en a
        sudo=True quand recherche de créneau depuis le site web.
        """
        self.ensure_one()
        if not self.duree:
            raise UserError(_("You must set a duration to search for available time slots."))

        # To avoid an access error from the website
        company = self.company_id if not sudo else self.company_id.sudo()
        if not company.partner_id.geo_lat and not company.partner_id.geo_lng:
            raise UserError(_(
                "The company address is not geocoded, please geocode it to plan an intervention. "
                "If an employee's address is not geocoded, we will use the company address instead "
                "to plan the intervention."))

        compare_precision = 5

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        employee_obj = self.env['hr.employee']
        wizard_line_obj = self.env['of.tournee.rdv.line']
        intervention_obj = self.with_context(force_read=True, virtual_id=True).env['of.planning.intervention']

        if sudo:
            employee_obj = employee_obj.sudo()
            intervention_obj = intervention_obj.sudo()

        # Suppression des anciens créneaux
        if mode == 'new':
            self.planning_ids.unlink()

        # Récupération des équipes
        tache_id = sudo and self.tache_id.sudo() or self.tache_id
        if not tache_id.employee_ids:
            if sudo:
                _logger.warning(u"Tentative ratée de recherche de créneau pour la tâche '%s': "
                                u"aucun intervenant ne peut la réaliser." % tache_id.name)
                return
            else:
                raise UserError(u"Aucun intervenant ne peut réaliser cette prestation.")
        employees = sudo and tache_id.employee_ids.sudo() or tache_id.employee_ids
        pre_employee_ids = sudo and self.pre_employee_ids.sudo() or self.pre_employee_ids
        if pre_employee_ids:
            employees &= pre_employee_ids
            if not employees:
                if sudo:
                    _logger.warning(u"Tentative ratée de recherche de créneau pour la tâche '%s': "
                                    u"aucun intervenant pré-sélectionné ne peut la réaliser." % tache_id.name)
                    return
                else:
                    raise UserError(
                        u"Aucun des intervenants sélectionnés n'a la compétence pour réaliser cette prestation.")

        # Jours du service, jours travaillés des équipes et horaires de travail
        jours_service = sudo and range(1, 8) or [jour.numero for jour in self.day_ids] or range(1, 8)

        jours_feries = self.company_id.get_jours_feries(self.date_recherche_debut, self.date_recherche_fin)
        passer_jours_feries = self.env['ir.values'].get_default('of.intervention.settings', 'ignorer_jours_feries')
        color_jours_feries = self.env['ir.values'].get_default('of.intervention.settings', 'color_jours_feries')

        un_jour = timedelta(days=1)
        # --- Création des créneaux de début et fin de recherche ---
        avant_recherche_da = fields.Date.from_string(self.date_recherche_debut) - un_jour
        avant_recherche = fields.Date.to_string(avant_recherche_da)
        # Il faut mettre les date de début et de fin des bornes en UTC pour utilisation par le JS
        avant_recherche_debut_dt = tz.localize(
            datetime.strptime(avant_recherche + " 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        avant_recherche_debut_dt = avant_recherche_debut_dt.astimezone(pytz.utc)  # passage en UTC
        avant_recherche_fin_dt = tz.localize(
            datetime.strptime(avant_recherche + " 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        avant_recherche_fin_dt = avant_recherche_fin_dt.astimezone(pytz.utc)  # passage en UTC
        apres_recherche_da = fields.Date.from_string(self.date_recherche_fin) + un_jour
        apres_recherche = fields.Date.to_string(apres_recherche_da)
        apres_recherche_debut_dt = tz.localize(
            datetime.strptime(apres_recherche + " 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        apres_recherche_debut_dt = apres_recherche_debut_dt.astimezone(pytz.utc)  # passage en UTC
        apres_recherche_fin_dt = tz.localize(
            datetime.strptime(apres_recherche + " 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        apres_recherche_fin_dt = apres_recherche_fin_dt.astimezone(pytz.utc)  # passage en UTC

        # create slots for search start and end, create slots for holidays
        wizard_line_obj.create({
            'name': u"Début de la recherche",
            'debut_dt': avant_recherche_debut_dt,
            'fin_dt': avant_recherche_fin_dt,
            'date_flo': 0.0,
            'date_flo_deadline': 23.9,
            'date': avant_recherche_da,
            'wizard_id': self.id,
            'employee_id': False,
            'intervention_id': False,
            'disponible': False,
            'allday': True,
        })
        wizard_line_obj.create({
            'name': "Fin de la recherche",
            'debut_dt': apres_recherche_debut_dt,
            'fin_dt': apres_recherche_fin_dt,
            'date_flo': 0.0,
            'date_flo_deadline': 23.9,
            'date': apres_recherche_da,
            'wizard_id': self.id,
            'employee_id': False,
            'intervention_id': False,
            'disponible': False,
            'allday': True,
        })
        for d in jours_feries:
            ferie_debut_dt = tz.localize(datetime.strptime(d + " 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
            ferie_debut_dt = ferie_debut_dt.astimezone(pytz.utc)
            ferie_fin_dt = tz.localize(datetime.strptime(d + " 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
            ferie_fin_dt = ferie_fin_dt.astimezone(pytz.utc)
            wizard_line_obj.create({
                'name': u"Férié: %s" % jours_feries[d].decode('utf-8'),
                'debut_dt': ferie_debut_dt,
                'fin_dt': ferie_fin_dt,
                'date_flo': 0.0,
                'date_flo_deadline': 23.99,
                'date': fields.Date.from_string(d),
                'wizard_id': self.id,
                'employee_id': False,
                'intervention_id': False,
                'disponible': False,
                'allday': True,
                'force_color': color_jours_feries,
            })

        # --- Recherche des créneaux ---
        date_recherche_da = avant_recherche_da
        # Parcourt tous les jours inclus entre la date de début de recherche et la date de fin de recherche.
        # Prend en compte les employés présélectionnés si il y en a et ceux qui peuvent effectuer la tache sinon
        while date_recherche_da < apres_recherche_da:
            date_recherche_da += un_jour
            num_jour = date_recherche_da.isoweekday()

            # Restriction aux jours spécifiés dans le service
            while num_jour not in jours_service:
                date_recherche_da += un_jour
                num_jour = ((num_jour + 1) % 7) or 7  # num jour de la semaine entre 1 et 7
            # Arreter la recherche si on dépasse la date de fin
            if date_recherche_da >= apres_recherche_da:
                continue
            date_recherche_str = fields.Date.to_string(date_recherche_da)
            seg_type = web and 'website' or 'regular'
            horaires_du_jour = employees.get_horaires_date(date_recherche_str, seg_type=seg_type)

            employees_dispo = [employee.id for employee in employees]

            # Contrôles liés à la prise de RDV en ligne
            if web:
                # Contrôle du mois
                allowed_month_ids = self.env['ir.values'].sudo().get_default(
                    'of.intervention.settings', 'website_booking_allowed_month_ids')
                allowed_months = self.env['of.mois'].sudo().browse(allowed_month_ids)
                if date_recherche_da.month not in allowed_months.mapped('numero'):
                    continue
                # Contrôle du jour
                allowed_day_ids = self.env['ir.values'].sudo().get_default(
                    'of.intervention.settings', 'website_booking_allowed_day_ids')
                allowed_days = self.env['of.jours'].sudo().browse(allowed_day_ids)
                if date_recherche_da.weekday() + 1 not in allowed_days.mapped('numero'):
                    continue
                # Contrôle des techniciens
                allowed_employee_ids = self.env['ir.values'].sudo().get_default(
                    'of.intervention.settings', 'website_booking_allowed_employee_ids') or []
                employees_dispo = list(set(employees_dispo) & set(allowed_employee_ids))

            # Recherche de créneaux pour la date voulue et les équipes sélectionnées
            jour_deb_dt = tz.localize(datetime.strptime(date_recherche_str + " 00:00:00", "%Y-%m-%d %H:%M:%S"))
            jour_fin_dt = tz.localize(datetime.strptime(date_recherche_str + " 23:59:00", "%Y-%m-%d %H:%M:%S"))
            # Récupération des interventions déjà planifiées, on exclut l'intervention reportée en
            # cours de replanification
            domain_interventions = [
                ('employee_ids', 'in', employees_dispo),
                ('date', '<=', date_recherche_str),
                ('date_deadline', '>=', date_recherche_str)]
            if self.origin_intervention_id:
                domain_interventions += [
                    '|',
                    ('id', '=', self.origin_intervention_id.id)]
            domain_interventions += [('state', 'not in', ('cancel', 'postponed'))]
            interventions = intervention_obj.search(domain_interventions, order='date')

            employee_intervention_dates = {employee_id: [] for employee_id in employees_dispo}
            for intervention in interventions:
                intervention_dates = [intervention]
                # read est détourné dans of_planning_recurring pour renvoyer les dates de l'occurence concernée
                # dans le cas des RDV recurrents
                data = intervention.read(['date_prompt', 'date_deadline_prompt'])[0]
                for intervention_date in (data['date_prompt'], data['date_deadline_prompt']):
                    # Conversion des dates de début et de fin en nombre flottant et à l'heure locale
                    date_intervention_locale_dt = fields.Datetime.context_timestamp(
                        self, fields.Datetime.from_string(intervention_date))

                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    date_intervention_locale_dt = max(date_intervention_locale_dt, jour_deb_dt)
                    date_intervention_locale_dt = min(date_intervention_locale_dt, jour_fin_dt)
                    date_intervention_locale_flo = round(date_intervention_locale_dt.hour +
                                                         date_intervention_locale_dt.minute / 60.0 +
                                                         date_intervention_locale_dt.second / 3600.0, 5)
                    intervention_dates.append(date_intervention_locale_flo)

                for employee_id in intervention.employee_ids.ids:
                    if employee_id in employees_dispo:
                        employee_intervention_dates[employee_id].append(intervention_dates)

            # Calcul des créneaux dispos et des créneaux occupés
            for employee in employee_obj.browse(employees_dispo):
                intervention_dates = employee_intervention_dates[employee.id]
                # On retrie la liste des RDV, car l'ordre naturel est erroné avec les RDV réguliers
                intervention_dates.sort(key=itemgetter(1))

                # Si paramètre secteur, on contrôle les tournées de l'intervenant
                if secteur_id:
                    tournee_obj = self.env['of.planning.tournee']
                    if sudo:
                        tournee_obj = tournee_obj.sudo()
                    tournee = tournee_obj.search([
                        ('date', '=', date_recherche_da),
                        ('employee_id', '=', employee.id),
                        ('sector_ids', 'in', [secteur_id])], limit=1)
                    if not tournee:
                        # si pas de tournée on prend un autre employé
                        continue
                    elif web:
                        # Dans le cadre de la prise de vRDV en ligne, on vérifie le paramètre journées vierges
                        allow_empty_days = self.env['ir.values'].sudo().get_default(
                            'of.intervention.settings', 'website_booking_allow_empty_days')
                        if not allow_empty_days and not tournee.intervention_ids:
                            continue

                horaires_employee = horaires_du_jour[employee.id]
                # ne pas calculer les créneau dispo les jours fériés si la case "ignorer jours fériés" est cochée
                if horaires_employee and not (passer_jours_feries and date_recherche_str in jours_feries):

                    index_courant = 0
                    deb, fin = horaires_employee[index_courant]  # horaires courants
                    creneaux = []
                    # @todo: Possibilité intervention chevauchant la nuit
                    for intervention, intervention_deb, intervention_fin in intervention_dates + [(False, 24, 24)]:
                        # Calcul du temps disponible avant l'intervention étudiée
                        # On saute les RDVs flexibles pour que leur créneau apparaisse comme dispo
                        if self.env.user.has_group('of_planning.of_group_planning_intervention_flexibility') and \
                                self.flexible and intervention and intervention.flexible:
                            continue
                        if float_compare(intervention_deb, deb, compare_precision) == 1:
                            # Un trou dans le planning, suffisant pour un créneau?
                            duree = 0.0
                            creneaux_temp = []
                            while float_compare(fin, intervention_deb, compare_precision) != 1:
                                # fin <= intervention_deb
                                # Le temps disponible est éclaté avec des temps de pause
                                duree += fin - deb
                                creneaux_temp.append((deb, fin))
                                index_courant += 1
                                if index_courant == len(horaires_employee):
                                    # L'intervention commence quand l'employé a déjà fini sa journée ...
                                    break
                                deb, fin = horaires_employee[index_courant]
                            else:
                                # L'intervention commence avant la fin du créneau courant
                                if float_compare(fin, intervention_deb, compare_precision) == 1 and \
                                        float_compare(deb, intervention_deb, compare_precision) != 0:
                                    # L'intervention commence au milieu du créneau courant (et pas en même temps!)
                                    duree += intervention_deb - deb
                                    creneaux_temp.append((deb, intervention_deb))
                            if float_compare(self.duree, duree, compare_precision) != 1:
                                # Le temps dégagé est suffisant pour la tâche à réaliser
                                creneaux += creneaux_temp
                        if index_courant == len(horaires_employee):
                            break

                        # Récupération du prochain créneau potentiellement disponible
                        deb = max(deb, intervention_fin)
                        while float_compare(fin, deb, compare_precision) != 1:
                            index_courant += 1
                            if index_courant == len(horaires_employee):
                                break
                            deb = max(deb, horaires_employee[index_courant][0])
                            fin = horaires_employee[index_courant][1]
                        if index_courant == len(horaires_employee):
                            break

                    # Création des créneaux disponibles
                    for intervention_deb, intervention_fin in creneaux:
                        description = "%s-%s" % tuple(hours_to_strs(intervention_deb, intervention_fin))

                        date_debut_dt = datetime.combine(date_recherche_da, datetime.min.time()) \
                            + timedelta(hours=intervention_deb)
                        date_debut_dt = tz.localize(date_debut_dt, is_dst=None).astimezone(pytz.utc)
                        date_fin_dt = datetime.combine(date_recherche_da, datetime.min.time()) \
                            + timedelta(hours=intervention_fin)
                        date_fin_dt = tz.localize(date_fin_dt, is_dst=None).astimezone(pytz.utc)

                        wizard_line_obj.create({
                            'debut_dt': date_debut_dt,
                            'fin_dt': date_fin_dt,
                            'date_flo': intervention_deb,
                            'date_flo_deadline': intervention_fin,
                            'date': date_recherche_str,
                            'description': description,
                            'wizard_id': self.id,
                            'employee_id': employee.id,
                            'intervention_id': False,
                        })
                # Création des créneaux d'intervention
                for intervention, intervention_deb, intervention_fin in intervention_dates:
                    description = "%s-%s" % tuple(hours_to_strs(intervention_deb, intervention_fin))

                    date_debut_dt = datetime.combine(date_recherche_da, datetime.min.time()) + timedelta(
                        hours=intervention_deb)
                    date_debut_dt = tz.localize(date_debut_dt, is_dst=None).astimezone(pytz.utc)
                    date_fin_dt = datetime.combine(date_recherche_da, datetime.min.time()) + timedelta(
                        hours=intervention_fin)
                    date_fin_dt = tz.localize(date_fin_dt, is_dst=None).astimezone(pytz.utc)

                    wizard_line_obj.create({
                        'debut_dt': date_debut_dt,  # datetime utc
                        'fin_dt': date_fin_dt,  # datetime utc
                        'date_flo': intervention_deb,
                        'date_flo_deadline': intervention_fin,
                        'date': date_recherche_str,
                        'description': description,
                        'wizard_id': self.id,
                        'employee_id': employee.id,
                        'intervention_id': calendar_id2real_id(intervention.id),
                        'name': intervention.name,
                        'disponible': False,
                    })
        # Calcul des durées et distances
        date_debut_da = avant_recherche_da + un_jour
        date_fin_da = apres_recherche_da - un_jour
        if not self.ignorer_geo:
            # Tester si le serveur de routage fonctionne
            routing_base_url = config.get("of_routing_base_url", "")
            routing_version = config.get("of_routing_version", "")
            routing_profile = config.get("of_routing_profile", "")
            if not (routing_base_url and routing_version and routing_profile):
                query = "null"
            else:
                query = routing_base_url + "nearest/" + routing_version + "/" + routing_profile + \
                    "/-1.72323900,48.17292300.json?number=1"
            query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
            try:
                req = requests.get(query_send, timeout=10)
                res = req.json()
                if res:
                    self.orthodromique = False
            except Exception:
                self.orthodromique = True
            self.calc_distances_dates_employees(date_debut_da, date_fin_da, employees, sudo=sudo)

        # Hide lines to limit the number of results in tree views
        nb, first_res = self.display_and_get_free_slots()

        # Sélection du résultat
        if nb > 0:
            if sudo:
                address = self.partner_address_id.sudo()
                name = address.name or (address.parent_id and address.parent_id.sudo().name) or ''
            else:
                address = sudo and self.partner_address_id.sudo() or self.partner_address_id
                name = address.name or (address.parent_id and address.parent_id.name) or ''
            name += address.zip and (" " + address.zip) or ""
            name += address.city and (" " + address.city) or ""

            first_res_da = fields.Date.from_string(first_res.date)
            # datetime naive
            date_propos_dt = datetime.combine(first_res_da, datetime.min.time()) + timedelta(hours=first_res.date_flo)
            # datetime utc
            date_propos_dt = tz.localize(date_propos_dt, is_dst=None).astimezone(pytz.utc)

            vals = {
                'date_display': first_res.date,
                'name': name,
                'employee_id': first_res.employee_id.id,
                'date_propos': date_propos_dt,  # datetime utc
                'date_propos_hour': first_res.date_flo,
                'res_line_id': first_res.id,
                'map_line_id': first_res.id,
                'map_tour_id': first_res.tour_id.id or False,
                'display_res': True,
                'zero_result': False,
            }

            if self.service_id and self.service_id.recurrence:
                if sudo:
                    vals['date_next'] = self.sudo().service_id.get_next_date(first_res_da.strftime('%Y-%m-%d'))
                    vals['date_fin_planif'] = self.sudo().service_id.get_fin_date(vals['date_next'])
                else:
                    vals['date_next'] = self.service_id.get_next_date(first_res_da.strftime('%Y-%m-%d'))
                    vals['date_fin_planif'] = self.service_id.get_fin_date(vals['date_next'])
            elif self.creer_recurrence:
                vals['date_next'] = "%s-%02i-01" % (first_res_da.year + 1, first_res_da.month)
                date_fin_planif_da = fields.Date.from_string(vals['date_next']) + relativedelta(months=1, days=-1)
                vals['date_fin_planif'] = fields.Date.to_string(date_fin_planif_da)
            else:
                vals['date_next'] = False

        else:
            vals = {
                'display_res': True,
                'zero_result': True,
            }

        self.write(vals)
        if self.res_line_id:
            self.res_line_id.selected = True
            self.res_line_id.selected_hour = self.res_line_id.date_flo
            self.map_tour_id = self.res_line_id.tour_id.id
            self.map_line_id = self.res_line_id.id
            # force the map to be recomputed
            self.sudo()._compute_intervention_map_data()
            # update OSRM data of the tour
            self.map_tour_id and self.map_tour_id.sudo()._check_missing_osrm_data()
            # get the route between the previous/next interventions and the one we are trying to schedule
            additional_geojson_data = self._get_additional_record_geojson_data(self.res_line_id)
            self.additional_record_geojson_data = additional_geojson_data

    @api.multi
    def _get_service_data(self, mois):
        """
        :param mois: mois de référence pour l'intervention récurrente
        :return: dictionnaires de valeurs pour la création d'intervention récurrente
        """
        return {
            'partner_id': self.partner_id.id,
            'address_id': self.partner_address_id.id,
            'company_id': self.company_id.id,
            'tache_id': self.tache_id.id,
            'type_id': self.env.ref('of_service.of_service_type_maintenance').id,
            'mois_ids': [(4, mois)],
            'date_next': self.date_next,
            'date_fin': self.date_fin_planif,
            'note': self.description or '',
            'base_state': 'calculated',
            'duree': self.duree,
            'recurrence': True,
        }

    @api.multi
    def get_values_intervention_create(self):
        """
        :return: dictionnaires de valeurs pour la création du RDV Tech
        """
        self.ensure_one()
        service = self.service_id
        if service and service.template_id:
            template_id = service.template_id.id
        else:
            template_id = self.template_id.id or False

        tag_ids = \
            [(4, tag.id) for tag in service.tag_ids] \
            if not self.origin_intervention_id else [(6, 0, self.origin_intervention_id.tag_ids.ids)]
        order_id = service.order_id.id if not self.origin_intervention_id else self.origin_intervention_id.order_id.id
        picking_list = service.order_id.picking_ids.ids if not self.origin_intervention_id \
            else self.origin_intervention_id.order_id.picking_ids.ids
        name = self.name if not self.origin_intervention_id else self.origin_intervention_id.name
        values = {
            'partner_id': self.partner_id.id,
            'address_id': self.partner_address_id.id,
            'tache_id': self.tache_id.id,
            'template_id': template_id,
            'service_id': service.id,
            'employee_ids': [(4, self.employee_id.id, 0)],
            'tag_ids': tag_ids,
            'date': self.date_propos,
            'duree': self.duree,
            'user_id': self._uid,
            'company_id': self.company_id.id,
            'name': name,
            'description': self.description or '',
            'state': 'confirm',
            'verif_dispo': True,
            'order_id': order_id,
            'picking_id': len(picking_list) == 1 and picking_list[0] or False,
            'origin_interface': u"Trouver un créneau (rdv.py)",
            'flexible': self.tache_id.flexible,
            'duration_one_way': self.res_line_id.duree_prec,
            'distance_one_way': self.res_line_id.dist_prec,
            'return_duration': self.res_line_id.duree_suiv,
            'return_distance': self.res_line_id.dist_suiv,
        }
        if self.origin_intervention_id:
            copied_lines = []
            for line in self.origin_intervention_id.line_ids:
                l_dict = line.copy_data()[0]
                l_dict.update({'intervention_id': False})
                copied_lines.append((0, 0, l_dict))
            values['line_ids'] = copied_lines
            copied_questions = []
            for question in self.origin_intervention_id.question_ids:
                q_dict = question.copy_data()[0]
                q_dict.update({'intervention_id': False})
                copied_questions.append((0, 0, q_dict))
            values['question_ids'] = copied_questions
        return values

    def _get_origin_arrival_addresses(self, sudo, employee, tournee):
        """ Get the origin and arrival addresses for searching the route.
        To avoid an error message during the search, we are trying to get a geocoded address.
        First we try to get the tour's address, then the address of the employee otherwise the address of
        the company is used. """
        self.ensure_one()
        origine = False
        arrivee = False
        # S'il y a une tournée, on favorise son point de départ plutôt que celui de l'employé.
        # Note : une tournée est unique par employé et par date (contrainte SQL) donc len(tournee) <= 1
        if sudo:
            # @todo: en l'état j'ai dû retirer la tournee pour contourner une erreur de droit,
            # il faut corriger ça
            if employee.of_address_depart_id.sudo() and employee.of_address_depart_id.sudo().geo_lat and \
                    employee.of_address_depart_id.sudo().geo_lng:
                origine = employee.of_address_depart_id.sudo()
            elif self.company_id.partner_id.sudo() and self.company_id.partner_id.sudo().geo_lat and \
                    self.company_id.partner_id.sudo().geo_lng:
                origine = self.company_id.partner_id.sudo()

            if employee.of_address_retour_id.sudo() and employee.of_address_retour_id.sudo().geo_lat and \
                    employee.of_address_retour_id.sudo().geo_lng:
                arrivee = employee.of_address_retour_id.sudo()
            elif self.company_id.partner_id.sudo() and self.company_id.partner_id.sudo().geo_lat and \
                    self.company_id.partner_id.sudo().geo_lng:
                arrivee = self.company_id.partner_id.sudo()
        else:
            # Take the tour's departure address if it exists else take the employee's departure address
            # otherwise take the company's departure address
            if tournee and tournee.start_address_id and tournee.start_address_id.geo_lat and \
                    tournee.start_address_id.geo_lng:
                origine = tournee.start_address_id
            elif employee.of_address_depart_id and employee.of_address_depart_id.geo_lat and \
                    employee.of_address_depart_id.geo_lng:
                origine = employee.of_address_depart_id
            elif self.company_id.partner_id and self.company_id.partner_id.geo_lat and \
                    self.company_id.partner_id.geo_lng:
                origine = self.company_id.partner_id

            # Take the tour's arrival address if it exists else take the employee's arrival address
            # otherwise take the company's arrival address
            if tournee and tournee.return_address_id and tournee.return_address_id.geo_lat and \
                    tournee.return_address_id.geo_lng:
                arrivee = tournee.return_address_id
            elif employee.of_address_retour_id and employee.of_address_retour_id.geo_lat and \
                    employee.of_address_retour_id.geo_lng:
                arrivee = employee.of_address_retour_id
            elif self.company_id.partner_id and self.company_id.partner_id.geo_lat and \
                    self.company_id.partner_id.geo_lng:
                arrivee = self.company_id.partner_id
        return origine, arrivee

    @api.multi
    def calc_distances_dates_employees(self, date_debut, date_fin, employees, sudo=False):
        u"""
            Appelle le serveur OSRM openfire pour calculer les distances des créneaux libres avec les RDV existants.
            Une requête http par jour et par employé.
            En cas de problème de performance on pourra se débrouiller pour faire une requête par employé.
        """
        self.ensure_one()
        wizard_line_obj = self.env['of.tournee.rdv.line']
        tournee_obj = self.env['of.planning.tournee']
        if sudo:
            tournee_obj = tournee_obj.sudo()
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        un_jour = timedelta(days=1)
        date_courante = date_debut
        employees = sudo and employees.sudo() or employees
        search_mode = self.search_mode
        while date_courante <= date_fin:
            for employee in employees:
                employee = sudo and employee.sudo() or employee
                # Ne pas prendre en compte les lignes allday qui ne sont pas liées à un RDV (jours fériés)
                creneaux = wizard_line_obj.search([
                    ('wizard_id', '=', self.id),
                    ('date', '=', date_courante),
                    ('employee_id', '=', employee.id),
                    '|', ('allday', '=', False), ('intervention_id', '!=', False)], order="debut_dt")
                if len(creneaux) == 0:
                    continue
                if not sudo:
                    tournee = tournee_obj.search([
                        ('date', '=', date_courante), ('employee_id', '=', employee.sudo().id)], limit=1)

                origine, arrivee = self._get_origin_arrival_addresses(sudo, employee, tournee)
                # Pas d'origine ni pour la tournée ni pour l'employé
                if not origine:
                    raise UserError(u"L'intervenant \"%s\" n'a pas d'adresse de départ." % employee.name)
                # Pas d'arrivée ni pour la tournée ni pour l'employé
                elif not arrivee:
                    raise UserError(u"L'intervenant \"%s\" n'a pas d'adresse d'arrivée." % employee.name)
                elif origine.geo_lat == origine.geo_lng == 0:
                    raise UserError(u"L'adresse de départ de l'intervenant \"%s\" n'est pas géolocalisée.\nDate : %s" %
                                    (employee.name, date_courante.strftime(lang.date_format)))
                elif arrivee.geo_lat == arrivee.geo_lng == 0:
                    raise UserError(u"L'adresse de retour de l'intervenant \"%s\" n'est pas géolocalisée.\nDate : %s" %
                                    (employee.name, date_courante.strftime(lang.date_format)))

                routing_base_url = config.get("of_routing_base_url", "")
                routing_version = config.get("of_routing_version", "")
                routing_profile = config.get("of_routing_profile", "")
                if not (routing_base_url and routing_version and routing_profile):
                    query = "null"
                else:
                    query = routing_base_url + "route/" + routing_version + "/" + routing_profile + "/"

                # Listes de coordonnées : ATTENTION OSRM prend ses coordonnées sous form (lng, lat)
                # Point de départ
                coords_str = str(origine.geo_lng) + "," + str(origine.geo_lat)
                coords = [{'lat': origine.geo_lat, 'lng': origine.geo_lng}]

                # Créneaux et interventions
                non_loc = False
                # Get the coordinates of the previous and next interventions to store them in the wizard_line
                # to be able to draw the route on the map to this slot in the tour's map view
                previous_line = False
                previous_geo_lng = origine.geo_lng
                previous_geo_lat = origine.geo_lat
                next_geo_lng = arrivee.geo_lng
                next_geo_lat = arrivee.geo_lat
                for index, line in enumerate(creneaux):
                    line_geo_lat = line.intervention_id.geo_lat if line.intervention_id else line.wizard_id.geo_lat
                    line_geo_lng = line.intervention_id.geo_lng if line.intervention_id else line.wizard_id.geo_lng
                    if index > 0 and creneaux[index - 1].intervention_id:
                        previous_line = creneaux[index - 1]
                        previous_geo_lng = previous_line.intervention_id.geo_lng
                        previous_geo_lat = previous_line.intervention_id.geo_lat
                    if not line.intervention_id:  # free slot
                        if index > 0 and index < len(creneaux) - 1:
                            next_line = creneaux[index + 1]
                            index_next = index + 1
                            while next_line.intervention_id is False:
                                index_next += 1
                                next_line = creneaux[index_next]
                                if index_next >= len(creneaux):
                                    break
                            if next_line.intervention_id:
                                next_geo_lng = next_line.intervention_id.geo_lng
                                next_geo_lat = next_line.intervention_id.geo_lat
                        elif index == len(creneaux) - 1:
                            next_geo_lng = arrivee.geo_lng
                            next_geo_lat = arrivee.geo_lat
                        line.write({
                            'previous_geo_lng': previous_geo_lng,
                            'previous_geo_lat': previous_geo_lat,
                            'next_geo_lng': next_geo_lng,
                            'next_geo_lat': next_geo_lat,
                        })
                    if line_geo_lat == line_geo_lng == 0:
                        non_loc = True
                        break
                    coords_str += ";" + str(line_geo_lng) + "," + str(line_geo_lat)
                    coords.append({'lat': line_geo_lat, 'lng': line_geo_lng})
                if non_loc:
                    continue

                # Point d'arrivée
                coords_str += ";" + str(arrivee.geo_lng) + "," + str(arrivee.geo_lat)
                coords.append({'lat': arrivee.geo_lat, 'lng': arrivee.geo_lng})

                legs = []
                res = {}
                if self.orthodromique:
                    for i in range(len(coords) - 1):
                        # Coords[i+1] existe toujours
                        dist = distance_points(coords[i]['lat'], coords[i]['lng'],
                                               coords[i + 1]['lat'], coords[i + 1]['lng'])
                        legs.append({'distance': dist * 1000, 'duration': -1})
                else:
                    query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
                    full_query = query_send + coords_str + "?"
                    try:
                        req = requests.get(full_query, timeout=10)
                        res = req.json()
                    except Exception:
                        res = {}

                if res and res.get('routes') or legs:
                    # a leg is a route between two waypoints.
                    legs = legs or res['routes'][0]['legs']
                    if len(creneaux) == len(legs) - 1:  # depart -> creneau -> arrivee : 2 routes 1 creneau
                        i = 0
                        len_slots = len(creneaux)
                        while i < len_slots:
                            crens = creneaux[i]
                            # Route : A ---> B ---> C ---> D
                            # leg 0 : A ---> B, leg 1 : B ---> C, ...
                            vals = {
                                'dist_prec': legs[i]['distance'] / 1000,
                                'duree_prec': legs[i]['duration'] / 60,
                            }
                            i += 1
                            if not crens.intervention_id:
                                # On regroupe les créneaux libres qui se suivent
                                while i < len_slots and not creneaux[i].intervention_id:
                                    crens |= creneaux[i]
                                    i += 1

                            # legs[i] ok car len(legs) == len(creneaux) + 1
                            vals['dist_suiv'] = legs[i]['distance'] / 1000
                            vals['duree_suiv'] = legs[i]['duration'] / 60
                            vals['distance'] = vals['dist_prec'] + vals['dist_suiv']
                            vals['duree'] = vals['duree_prec'] + vals['duree_suiv']
                            duree_dispo = sum([c.date_flo_deadline - c.date_flo for c in crens])

                            if crens[0].disponible:
                                if search_mode == 'oneway':
                                    vals['distance_utile'] = vals['dist_prec']
                                    vals['duree_utile'] = vals['duree_prec']
                                elif search_mode == 'return':
                                    vals['distance_utile'] = vals['dist_suiv']
                                    vals['duree_utile'] = vals['duree_suiv']
                                elif search_mode == 'round_trip':
                                    vals['distance_utile'] = vals['distance']
                                    vals['duree_utile'] = vals['duree']
                                elif search_mode == 'oneway_or_return':
                                    vals['distance_utile'] = min(vals['dist_prec'], vals['dist_suiv'])
                                    vals['duree_utile'] = min(vals['duree_prec'], vals['duree_suiv'])
                                elif search_mode == 'oneway_am_return_pm':
                                    if crens[0].date_flo <= AM_LIMIT_FLOAT:  # one way, if morning
                                        vals['distance_utile'] = vals['dist_prec']
                                        vals['duree_utile'] = vals['duree_prec']
                                    else:  # return, if afternoon
                                        vals['distance_utile'] = vals['dist_suiv']
                                        vals['duree_utile'] = vals['duree_suiv']

                                # Trajet aller-retour plus long que la durée de l'intervention
                                if vals['duree'] > duree_dispo * 60:
                                    # note: On vérifie si la durée de transport est inférieure à la durée du créneau.
                                    #   Cela a peu de sens si on ignore la durée réelle nécessaire pour l'intervention.
                                    #     (par exemple si le temps de trajet laisse 5 minutes pour l'intervention)
                                    #   Idéalement, la durée de la tâche ne devrait plus inclure le temps de transport
                                    #     mais le temps de transport devrait être laissé libre entre 2 interventions
                                    #     (ou ajouter une intervention de type 'transport'?... mise en place compliquée)
                                    vals['force_color'] = "#AA0000"
                                    vals['name'] = "TROP COURT"
                                    vals['disponible'] = False
                            crens.update(vals)
                else:
                    raise UserWarning("Erreur inattendue de routing")
            date_courante += un_jour

    @api.multi
    def display_and_get_free_slots(self):
        """Returns the number of slots available (that match the search criteria),
        and the first result (depending on search type)"""
        self.ensure_one()
        search_order_str = 'distance_utile, debut_dt, employee_id' if self.search_type == 'distance' \
            else 'duree_utile, debut_dt, employee_id'
        # number max of results to display
        number_of_results = self.env['ir.values'].get_default('of.intervention.settings', 'number_of_results')
        # get all available lines neither linked to an intervention nor to the search start/stop bounds
        lines = self.env['of.tournee.rdv.line'].search([
            ('wizard_id', '=', self.id),
            ('disponible', '=', True),
            ('allday', '=', False),
            ('intervention_id', '=', False)], order=search_order_str)
        # total number of available slots (that match the search criteria)
        nb = len(lines)
        first_slot = lines and lines[0] or False
        # update lines to hide the lines who are above the number_of_results
        by_date_lines_hidden, by_distance_lines_hidden, by_duration_lines_hidden = self._get_hidden_lines(
            search_order_str)
        by_date_lines_hidden[:number_of_results].write({'by_date_hidden': False})
        by_distance_lines_hidden[:number_of_results].write({'by_distance_hidden': False})
        by_duration_lines_hidden[:number_of_results].write({'by_duration_hidden': False})
        return nb, first_slot


class OfTourneeRdvLineMixin(models.AbstractModel):
    _name = 'of.tournee.rdv.line.mixin'
    _description = u"Mixin pour la propositions des RDVs"

    @api.multi
    def toggl_map_preview(self):
        """Helper to set a decoration style on the line that was clicked"""
        self.ensure_one()
        self.search([('wizard_id', '=', self.wizard_id.id), ('map_preview', '=', True)]).write({'map_preview': False})
        self.map_preview = True

    @api.multi
    def action_view_tour(self):
        """Update the map on the right side of the list view. That should display the tour of the current intervenant"""
        self.ensure_one()
        self.wizard_id.map_tour_id = self.tour_id.id or False
        self.wizard_id.map_line_id = self.id
        # force the map to be recomputed
        self.wizard_id.sudo()._compute_intervention_map_data()
        self.toggl_map_preview()
        # update OSRM data of the tour
        self.tour_id and self.tour_id.sudo()._check_missing_osrm_data()
        # get the route between the previous/next interventions and the meet we are trying to schedule
        additional_geojson_data = self.wizard_id._get_additional_record_geojson_data(self)
        self.wizard_id.additional_record_geojson_data = additional_geojson_data
        return self.wizard_id.action_open_wizard()

    @api.multi
    def action_select_confirm_slot(self):
        self.ensure_one()
        self.button_select()
        return self.button_confirm()

    @api.multi
    def button_confirm(self):
        """Sélectionne ce créneau en tant que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        d = fields.Date.from_string(self.date)
        date_propos_dt = datetime.combine(
            d, datetime.min.time()) + timedelta(hours=self.selected_hour)  # datetime local
        date_propos_dt = tz.localize(date_propos_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc
        self.wizard_id.date_propos = date_propos_dt
        return self.wizard_id.button_confirm()

    @api.multi
    def button_select(self, sudo=False):
        """Sélectionne ce créneau en tant que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        selected_line = self.search([('wizard_id', '=', self.wizard_id.id), ('selected', '=', True)])
        selected_line.write({'selected': False})
        self.selected = True
        self.selected_hour = self.date_flo

        if sudo:
            address = self.wizard_id.partner_address_id.sudo()
            name = address.name or (address.parent_id and address.parent_id.sudo().name) or ''
        else:
            address = self.wizard_id.partner_address_id
            name = address.name or (address.parent_id and address.parent_id.name) or ''
        name += address.zip and (" " + address.zip) or ""
        name += address.city and (" " + address.city) or ""
        # if we are on the delegated object we must use the id of the parent object
        res_line_id = self.id
        wizard_vals = {
            'date_display': self.date,
            'name': name,
            'employee_id': self.employee_id.id,
            'date_propos': self.debut_dt,
            'date_propos_hour': self.date_flo,
            'res_line_id': res_line_id,
            'map_line_id': res_line_id,
            'map_tour_id': self.tour_id.id or False
        }
        self.wizard_id.write(wizard_vals)
        return {'type': 'ir.actions.do_nothing'}


class OfTourneeRdvLine(models.TransientModel):
    _name = 'of.tournee.rdv.line'
    _description = u"Propositions des RDVs"
    _inherit = ['of.calendar.mixin', 'of.tournee.rdv.line.mixin']

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
    tour_id = fields.Many2one(
        comodel_name='of.planning.tournee', string="Tour", compute='_compute_tour_id', store=True)
    date = fields.Date(string="Date", index=True)
    debut_dt = fields.Datetime(string=u"Début")
    fin_dt = fields.Datetime(string="Fin")
    date_flo = fields.Float(string='Date', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    description = fields.Char(string=u"Créneau", size=128)
    wizard_id = fields.Many2one(
        comodel_name='of.tournee.rdv', string="RDV", required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Intervenant')
    employee_cal_ids = fields.Many2many(
        comodel_name='hr.employee', compute='_compute_cal_employee_ids', string="Intervenants",
        help="Technical field used to display attendees and colors in calendar view")
    intervention_id = fields.Many2one(comodel_name='of.planning.intervention', string="Planning", index=True)
    name = fields.Char(string="name", default="DISPONIBLE")
    distance = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    dist_prec = fields.Float(string='Dist.Prec. (km)', digits=(12, 0))
    dist_suiv = fields.Float(string='Dist.Suiv. (km)', digits=(12, 0))
    dist_ortho = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    dist_ortho_prec = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    dist_ortho_suiv = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    duree = fields.Float(string=u'Durée.tot. (min)', default=-1, digits=(12, 0), help=u"durée prec + durée suiv")
    previous_geo_lat = fields.Float(string="Latitude of the previous intervention")
    previous_geo_lng = fields.Float(string="Longitude of the previous intervention")
    next_geo_lat = fields.Float(string="Latitude of the next intervention")
    next_geo_lng = fields.Float(string="Longitude of the next intervention")
    duree_prec = fields.Float(string=u'Durée.Prec. (min)', digits=(12, 0))
    duree_suiv = fields.Float(string=u'Durée.Suiv. (min)', digits=(12, 0))
    distance_utile = fields.Float(string=u"Dist. utile (km)", digits=(12, 0))
    duree_utile = fields.Float(string=u'Durée. utile (min)', digits=(12, 0))
    of_color_ft = fields.Char(related="employee_id.of_color_ft", readonly=True)
    of_color_bg = fields.Char(related="employee_id.of_color_bg", readonly=True)
    disponible = fields.Boolean(string="Est dispo", default=True, index=True)
    map_preview = fields.Boolean(string="Map preview", default=False)
    force_color = fields.Char("Couleur")
    by_distance_hidden = fields.Boolean(string="Hidden", default=True, index=True)
    by_duration_hidden = fields.Boolean(string="Hidden", default=True, index=True)
    by_date_hidden = fields.Boolean(string="Hidden", default=True, index=True)
    allday = fields.Boolean('All Day', default=False, index=True)
    selected = fields.Boolean(u'Créneau sélectionné', default=False)
    selected_hour = fields.Float(string='Heure du RDV', digits=(2, 2))
    selected_description = fields.Text(string="Description", related="wizard_id.description")

    @api.multi
    @api.depends('date')
    def _compute_date_weekday(self):
        for record in self:
            if not self._context.get('tz'):
                self = self.with_context(tz='Europe/Paris')
            day_value = False
            if record.date:
                day_value = WEEKDAYS_TR[fields.Date.from_string(record.date).strftime('%A').capitalize()]
            record.weekday = day_value

    # @api.depends

    @api.depends('intervention_id')
    def _compute_state_int(self):
        """de of.calendar.mixin"""
        for line in self:
            interv = line.intervention_id
            if interv:
                if interv.state and interv.state == 'draft':
                    line.state_int = 0
                elif interv.state and interv.state == 'confirm':
                    line.state_int = 1
                elif interv.state and interv.state in ('done', 'unfinished'):
                    line.state_int = 2
            else:
                line.state_int = 3

    @api.multi
    def _compute_cal_employee_ids(self):
        for line in self:
            employee_ids = line.wizard_id._get_employee_possible()
            line.employee_cal_ids = line.employee_id or self.env['hr.employee'].browse(employee_ids)

    @api.depends('date', 'employee_id')
    def _compute_tour_id(self):
        for line in self:
            sql_result = False
            if line.employee_id:
                self._cr.execute(
                    "SELECT id FROM of_planning_tournee WHERE date = %s AND employee_id = %s LIMIT 1",
                    (line.date, line.employee_id.id))
                sql_result = self._cr.fetchone()
            line.tour_id = sql_result and sql_result[0] or False

    # Autres

    @api.model
    def get_state_int_map(self):
        """de of.calendar.mixin"""
        v0 = {'label': 'Brouillon', 'value': 0}
        v1 = {'label': u'Confirmé', 'value': 1}
        v2 = {'label': u'Réalisé', 'value': 2}
        v3 = {'label': u'Disponibilité', 'value': 3}
        return v0, v1, v2, v3
