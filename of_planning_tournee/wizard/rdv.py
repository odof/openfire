# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import pytz
from odoo.exceptions import UserError
from odoo.addons.of_geolocalize.models.of_geo import GEO_PRECISION
from odoo.addons.of_utils.models.of_utils import distance_points, hours_to_strs


import urllib
import requests

from odoo.tools import config
from odoo.tools.float_utils import float_compare

SEARCH_MODES = [
    ('distance', u'Distance (km)'),
    ('duree', u'Durée (min)'),
]

"""
bug description quand changement de tache ou service lié puis changé?
# refonte employés et équipes: dans un premier temp, on limite la prise de rdv aux tache à 1 intervenant
"""


class OfTourneeRdv(models.TransientModel):
    _name = 'of.tournee.rdv'
    _description = u'Prise de RDV dans les tournées'

    @api.model
    def default_get(self, fields=None):
        res = super(OfTourneeRdv, self).default_get(fields)
        # Suivant que la prise de rdv se fait depuis la fiche client ou une intervention à programmer
        service_obj = self.env['of.service']
        partner_obj = self.env['res.partner']
        active_model = self._context.get('active_model', '')
        service = False
        partner = False
        address = False
        if active_model == 'res.partner':
            partner_id = self._context['active_ids'][0]
            partner = partner_obj.browse(partner_id)
            service = service_obj.search([('partner_id', '=', partner.id), ('recurrence', '=', True)], limit=1)
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])
        elif active_model == 'of.service':
            service_id = self._context['active_ids'][0]
            service = service_obj.browse(service_id)
            partner = service.partner_id
            address = service.address_id
        elif active_model == 'sale.order':
            order_id = self._context['active_ids'][0]
            order = self.env['sale.order'].browse(order_id)
            partner = order.partner_id
            service = service_obj.search([('order_id', '=', order_id)], limit=1)
            if not service:
                service = service_obj.search([('partner_id', '=', partner.id)], limit=1)
            address = order.partner_shipping_id or order.partner_id

        if address and not (address.geo_lat or address.geo_lng):
            address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
                                          '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)],
                                         limit=1) or address

        res['partner_id'] = partner and partner.id or False
        res['partner_address_id'] = address and address.id or False
        res['service_id'] = service and service.id or False
        return res

    # Champs de recherche

    partner_id = fields.Many2one(
        'res.partner', string="Client", required=True, readonly=True)
    partner_address_id = fields.Many2one(
        'res.partner', string="Adresse d'intervention", required=True,
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    geo_lat = fields.Float(related='partner_address_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='partner_address_id.geo_lng', readonly=True)
    precision = fields.Selection(related='partner_address_id.precision', readonly=True)
    geocode_retry = fields.Boolean(u"Geocodage retenté", compute="_compute_geocode_retry")
    ignorer_geo = fields.Boolean(u"Ignorer données géographiques")
    partner_address_street = fields.Char(related="partner_address_id.street", readonly=True)
    partner_address_street2 = fields.Char(related="partner_address_id.street2", readonly=True)
    partner_address_city = fields.Char(related="partner_address_id.city", readonly=True)
    partner_address_state_id = fields.Many2one(related="partner_address_id.state_id", readonly=True)
    partner_address_zip = fields.Char(related="partner_address_id.zip", readonly=True)
    partner_address_country_id = fields.Many2one(related="partner_address_id.country_id", readonly=True)
    service_id = fields.Many2one('of.service', string=u"À programmer", domain="[('partner_id', '=', partner_id)]")
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche", required=True)
    creer_recurrence = fields.Boolean(
        string=u"Créer récurrence?",
        help=u"Créera une intervention récurrente s'il n'en existe pas déjà une associée à ce RDV.")
    duree = fields.Float(string=u'Durée', required=True, digits=(12, 5))
    pre_employee_ids = fields.Many2many(
        'hr.employee', string=u"Pré-sélection d'intervenants",
        domain="['|', ('of_tache_ids', 'in', tache_id), ('of_toutes_taches', '=', True)]",
        help=u"Pré-sélection des intervenants")

    date_recherche_debut = fields.Date(
        string=u"À partir du", required=True,
        default=lambda *a: (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'))
    date_recherche_fin = fields.Date(
        string="Jusqu'au", required=True, default=lambda *a: (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'))
    mode_recherche = fields.Selection(SEARCH_MODES, string="Mode de recherche", required=True, default="distance")
    max_recherche = fields.Float(string="Maximum")
    orthodromique = fields.Boolean(string=u"Distances à vol d'oiseau")

    # Champs de résultat

    display_res = fields.Boolean(string=u"Voir Résultats", default=False)  # Utilisé pour attrs invisible des résultats
    zero_result = fields.Boolean(string="Recherche infructueuse", default=False, help=u"Aucun résultat")
    zero_dispo = fields.Boolean(
        string="Recherche infructueuse", default=False, help=u"Aucun résultat suffisamment proche")
    planning_ids = fields.One2many('of.tournee.rdv.line', 'wizard_id', string='Proposition de RDVs')
    planning_tree_ids = fields.One2many(
        'of.tournee.rdv.line', 'wizard_id', string='Proposition de RDVs',
        domain=[('intervention_id', '=', False), ('allday', '=', False)])
    res_line_id = fields.Many2one("of.tournee.rdv.line", string=u"Créneau Sélectionné")

    name = fields.Char(string=u"Libellé", size=64, required=False)
    description = fields.Html(string="Description")
    employee_id = fields.Many2one('hr.employee', string=u"Intervenant")
    date_propos = fields.Datetime(string=u"RDV Début")
    date_propos_hour = fields.Float(string=u"Heure de début", digits=(12, 5))
    date_display = fields.Char(string="Jour du RDV", size=64, readonly=True)

    # champs pour la création ou mise à jour d'interventions récurrentes
    date_next = fields.Date(
        string=u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention")
    date_fin_planif = fields.Date(
        string=u'expiration de prochaine planif', help=u"Date à partir de laquelle l'intervention devient en retard")

    # @api.depends

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

    # @api.onchange

    @api.onchange('service_id')
    def _onchange_service(self):
        """Affecte la tâche, la description et l'adresse"""
        if not self.service_id:
            return

        service = self.service_id
        notes = [service.tache_id.name]
        if service.note:
            notes.append(service.note)

        vals = {
            'description': "\n".join(notes),
            'tache_id': service.tache_id,
            'partner_address_id': service.address_id,
        }
        self.update(vals)

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        """Affecte creer_recurrence, duree et pre_employee_ids"""
        service_obj = self.env['of.service']
        vals = {'service_id': False}
        if self.tache_id:
            if self.service_id and self.service_id.tache_id.id == self.tache_id.id:
                del vals['service_id']
            else:
                service = service_obj.search([('partner_id', '=', self.partner_id.id),
                                              ('tache_id', '=', self.tache_id.id)], limit=1)
                if service:
                    vals['service_id'] = service

            if vals.get('service_id', self.service_id):
                vals['creer_recurrence'] = False
            else:
                # Si il n'y a pas d'a_programmer, on affecte creer_recurrence en fonction de la tâche
                vals['creer_recurrence'] = self.tache_id.recurrence

            if self.tache_id.duree:
                vals['duree'] = self.tache_id.duree

            employees = []
            for employee in self.pre_employee_ids:
                if employee in self.tache_id.employee_ids:
                    employees.append(employee.id)
            vals['pre_employee_ids'] = employees
        self.update(vals)

    @api.onchange('date_recherche_debut')
    def _onchange_date_recherche_debut(self):
        """Affecte date_recherche_fin"""
        self.ensure_one()
        if self.date_recherche_debut:
            date_deb = fields.Date.from_string(self.date_recherche_debut)
            date_fin = date_deb + timedelta(days=6)
            self.date_recherche_fin = fields.Date.to_string(date_fin)

    @api.onchange('date_recherche_fin')
    def _onchange_date_recherche_fin(self):
        """Vérifie la cohérence des dates de recherche"""
        self.ensure_one()
        if self.date_recherche_fin and self.date_recherche_fin < self.date_recherche_debut:
            raise UserError(u"La date de fin de recherche doit être postérieure à la date de début de recherche")

    @api.onchange('mode_recherche')
    def _onchange_mode_recherche(self):
        """Affecte max_recherche"""
        self.ensure_one()
        if self.mode_recherche:
            self.max_recherche = self.mode_recherche == 'distance' and 50 or 60

    # Actions

    @api.multi
    def button_geocode(self):
        """Géocode le partenaire"""
        self.ensure_one()
        if self.geocode_retry:
            raise UserError("Votre géocodeur par défaut n'a pas réussi a géocoder cette adresse")
        self.partner_address_id.geo_code()
        self.geocode_retry = True
        if self.geo_lat != 0 or self.geo_lng != 0:
            self.ignorer_geo = False
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_calcul(self):
        """
        Lance la recherche de créneaux dispos
        @todo: Remplacer le retour d'action par un return True, mais pour l'instant cela
          ne charge pas correctement la vue du planning.
        """
        self.compute()
        context = dict(self._context, employee_domain=self._get_employee_possible())
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.tournee.rdv',
            'view_type': 'form',
            'view_mode': 'form',
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
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        intervention_obj = self.env['of.planning.intervention']
        service_obj = self.env['of.service']

        # Vérifier que la date de début et la date de fin sont dans les créneaux
        employee = self.employee_id
        if not employee.of_segment_ids:
            raise UserError("Il faut configurer l'horaire de travail de tous les intervenants.")

        date_propos_dt = fields.Datetime.from_string(self.date_propos)  # datetime utc proposition de rdv

        values = self.get_values_intervention_create()

        res = intervention_obj.create(values)
        contract_custom = self.sudo().env['ir.module.module'].search([('name', '=', 'of_contract_custom')])

        # Creation/mise à jour du service si creer_recurrence
        if self.date_next:
            if self.service_id:
                self.service_id.write({
                    'date_next': self.date_next,
                    'date_fin': self.date_fin_planif
                })
            elif self.creer_recurrence and (not contract_custom or contract_custom.state != 'installed'):
                res.service_id = service_obj.create(self._get_service_data(date_propos_dt.month))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.planning.intervention',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': res.id,
            'target': 'current',
            'context': self._context
        }

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
    def compute(self):
        u"""
        Remplit le champ planning_ids avec les créneaux non travaillés et les RDV tech.
        Lance le calcul des distances et sélectionne un résultat si il y en a
        """
        self.ensure_one()
        compare_precision = 5

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        employee_obj = self.env['hr.employee']
        wizard_line_obj = self.env['of.tournee.rdv.line']
        intervention_obj = self.env['of.planning.intervention']

        service = self.service_id

        # Suppression des anciens créneaux
        self.planning_ids.unlink()

        # Récupération des équipes
        if not self.tache_id.employee_ids:
            raise UserError(u"Aucun intervenant ne peut réaliser cette prestation.")
        employees = self.tache_id.employee_ids
        if self.pre_employee_ids:
            employees &= self.pre_employee_ids
            if not employees:
                raise UserError(u"Aucun des intervenants sélectionnés n'a la compétence pour réaliser cette prestation.")

        # Jours du service, jours travaillés des équipes et horaires de travail
        jours_service = [jour.numero for jour in service.jour_ids] if service else range(1, 8)

        un_jour = timedelta(days=1)
        # --- Création des créneaux de début et fin de recherche ---
        avant_recherche_da = fields.Date.from_string(self.date_recherche_debut) - un_jour
        avant_recherche = fields.Date.to_string(avant_recherche_da)
        avant_recherche_debut_dt = tz.localize(datetime.strptime(avant_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        avant_recherche_fin_dt = tz.localize(datetime.strptime(avant_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        apres_recherche_da = fields.Date.from_string(self.date_recherche_fin) + un_jour
        apres_recherche = fields.Date.to_string(apres_recherche_da)
        apres_recherche_debut_dt = tz.localize(datetime.strptime(apres_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        apres_recherche_fin_dt = tz.localize(datetime.strptime(apres_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime

        for employee in employees:
            wizard_line_obj.create({
                'name': u"Début de la recherche",
                'debut_dt': avant_recherche_debut_dt,
                'fin_dt': avant_recherche_fin_dt,
                'date_flo': 0.0,
                'date_flo_deadline': 23.9,
                'date': avant_recherche_da,
                'wizard_id': self.id,
                'employee_id': employee.id,
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
                'employee_id': employee.id,
                'intervention_id': False,
                'disponible': False,
                'allday': True,
            })

        # --- Recherche des créneaux ---
        date_recherche_da = avant_recherche_da
        u"""
        Parcourt tous les jours inclus entre la date de début de recherche et la date de fin de recherche.
        Prend en compte les employés présélectionnés si il y en a et ceux qui peuvent effectuer la tache sinon
        """
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
            horaires_du_jour = employees.get_horaires_date(date_recherche_str)

            employees_dispo = [employee.id for employee in employees]

            # Recherche de créneaux pour la date voulue et les équipes sélectionnées
            jour_deb_dt = tz.localize(datetime.strptime(date_recherche_str+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
            jour_fin_dt = tz.localize(datetime.strptime(date_recherche_str+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
            # Récupération des interventions déjà planifiées
            interventions = intervention_obj.search([('employee_ids', 'in', employees_dispo),
                                                     ('date', '<=', date_recherche_str),
                                                     ('date_deadline', '>=', date_recherche_str),
                                                     ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                                     ], order='date')

            employee_intervention_dates = {employee_id: [] for employee_id in employees_dispo}
            for intervention in interventions:
                intervention_dates = [intervention]
                for intervention_date in (intervention.date, intervention.date_deadline):
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

            # Calcul des créneaux dispos
            for employee in employee_obj.browse(employees_dispo):
                intervention_dates = employee_intervention_dates[employee.id]

                horaires_employee = horaires_du_jour[employee.id]
                if horaires_employee:

                    index_courant = 0
                    deb, fin = horaires_employee[index_courant]  # horaires courants
                    creneaux = []
                    # @todo: Possibilité intervention chevauchant la nuit
                    for intervention, intervention_deb, intervention_fin in intervention_dates + [(False, 24, 24)]:
                        # Calcul du temps disponible avant l'intervention étudiée
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

                        date_debut_dt = datetime.combine(date_recherche_da, datetime.min.time())\
                                        + timedelta(hours=intervention_deb)
                        date_debut_dt = tz.localize(date_debut_dt, is_dst=None).astimezone(pytz.utc)
                        date_fin_dt = datetime.combine(date_recherche_da, datetime.min.time())\
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

                    date_debut_dt = datetime.combine(date_recherche_da, datetime.min.time()) + timedelta(hours=intervention_deb)
                    date_debut_dt = tz.localize(date_debut_dt, is_dst=None).astimezone(pytz.utc)
                    date_fin_dt = datetime.combine(date_recherche_da, datetime.min.time()) + timedelta(hours=intervention_fin)
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
                        'intervention_id': intervention.id,
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
            except Exception as e:
                self.orthodromique = True
            self.calc_distances_dates_employees(date_debut_da, date_fin_da, employees)

        nb, nb_dispo, first_res = wizard_line_obj.get_nb_dispo(self)

        # Sélection du résultat
        if nb > 0:
            address = self.partner_address_id
            name = address.name or (address.parent_id and address.parent_id.name) or ''
            name += address.zip and (" " + address.zip) or ""
            name += address.city and (" " + address.city) or ""

            first_res_da = fields.Date.from_string(first_res.date)
            date_propos_dt = datetime.combine(first_res_da, datetime.min.time()) + timedelta(hours=first_res.date_flo)  # datetime naive
            date_propos_dt = tz.localize(date_propos_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc

            vals = {
                'date_display'    : first_res.date,
                'name'            : name,
                'employee_id'     : first_res.employee_id.id,
                'date_propos'     : date_propos_dt,  # datetime utc
                'date_propos_hour': first_res.date_flo,
                'res_line_id'     : first_res.id,
                'display_res'     : True,
                'zero_result'     : False,
                'zero_dispo'      : False,
            }

            if self.service_id and self.service_id.recurrence:
                vals['date_next'] = self.service_id.get_next_date(first_res_da.strftime('%Y-%m-%d'))
                vals['date_fin_planif'] = self.service_id.get_fin_date(vals['date_next'])
            elif self.creer_recurrence:
                vals['date_next'] = "%s-%02i-01" % (first_res_da.year + 1, first_res_da.month)
                date_fin_planif_da = fields.Date.from_string(vals['date_next']) + relativedelta(months=1, days=-1)
                vals['date_fin_planif'] = fields.Date.to_string(date_fin_planif_da)
            else:
                vals['date_next'] = False

            if nb_dispo == 0:
                vals['display_res'] = True
                vals['zero_dispo'] = True

        else:
            vals = {
                'display_res': True,
                'zero_result': True,
                'zero_dispo': False,
            }

        self.write(vals)
        if self.res_line_id:
            self.res_line_id.selected = True
            self.res_line_id.selected_hour = self.res_line_id.date_flo

    @api.multi
    def _get_service_data(self, mois):
        """
        :param mois: mois de référence pour l'intervention récurrente
        :return: dictionnaires de valeurs pour la création d'intervention récurrente
        """
        return {
            'partner_id': self.partner_id.id,
            'address_id': self.partner_address_id.id,
            'tache_id': self.tache_id.id,
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
        return {
            'partner_id': self.partner_id.id,
            'address_id': self.partner_address_id.id,
            'tache_id': self.tache_id.id,
            'service_id': self.service_id.id,
            'employee_ids': [(4, self.employee_id.id, 0)],
            'date': self.date_propos,
            'duree': self.duree,
            'user_id': self._uid,
            'company_id': self.partner_address_id.company_id and self.partner_address_id.company_id.id,
            'name': self.name,
            'description': self.description or '',
            'state': 'confirm',
            'verif_dispo': True,
            'order_id': self.service_id.order_id.id,
            'origin_interface': u"Trouver un créneau (rdv.py)",
        }

    @api.multi
    def calc_distances_dates_employees(self, date_debut, date_fin, employees):
        u"""
            Appelle le serveur OSRM openfire pour calculer les distances des créneaux libres avec les RDV existants.
            Une requête http par jour et par employé.
            En cas de problème de performance on pourra se débrouiller pour faire une requête par employé.
        """
        self.ensure_one()
        wizard_line_obj = self.env['of.tournee.rdv.line']
        tournee_obj = self.env['of.planning.tournee']
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        un_jour = timedelta(days=1)
        date_courante = date_debut
        while date_courante <= date_fin:
            mode_recherche = self.orthodromique and "distance" or self.mode_recherche
            maxi = self.max_recherche
            for employee in employees:
                creneaux = wizard_line_obj.search([('wizard_id', '=', self.id),
                                                   ('date', '=', date_courante),
                                                   ('employee_id', '=', employee.id)], order="debut_dt")
                if len(creneaux) == 0:
                    continue
                tournee = tournee_obj.search([('date', '=', date_courante),
                                              ('employee_id', '=', employee.id)], limit=1)
                # S'il y a une tournée, on favorise son point de départ plutôt que celui de l'employé.
                # Note : une tournée est unique par employé et par date (contrainte SQL) donc len(tournee) <= 1
                origine = (tournee and tournee.address_depart_id or
                           employee.of_address_depart_id or
                           False)
                arrivee = (tournee and tournee.address_retour_id or
                           employee.of_address_retour_id or
                           False)
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
                for line in creneaux:
                    if line.geo_lat == line.geo_lng == 0:
                        non_loc = True
                        break
                    coords_str += ";" + str(line.geo_lng) + "," + str(line.geo_lat)
                    coords.append({'lat': line.geo_lat, 'lng': line.geo_lng})
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
                    legs = legs or res['routes'][0]['legs']
                    if len(creneaux) == len(legs) - 1:  # depart -> creneau -> arrivee : 2 routes 1 creneau
                        i = 0
                        l = len(creneaux)
                        while i < l:
                            crens = creneaux[i]
                            vals = {
                                'dist_prec': legs[i]['distance'] / 1000,
                                'duree_prec': legs[i]['duration'] / 60,
                            }
                            i += 1
                            if not crens.intervention_id:
                                # On regroupe les créneaux libres qui se suivent
                                while i < l and not creneaux[i].intervention_id:
                                    crens |= creneaux[i]
                                    i += 1
                            vals['dist_suiv'] = legs[i]['distance'] / 1000  # legs[i] ok car len(legs) == len(creneaux) + 1
                            vals['duree_suiv'] = legs[i]['duration'] / 60
                            vals['distance'] = vals['dist_prec'] + vals['dist_suiv']
                            vals['duree'] = vals['duree_prec'] + vals['duree_suiv']
                            duree_dispo = sum([c.date_flo_deadline - c.date_flo for c in crens])

                            if crens[0].disponible:
                                if mode_recherche == 'distance' and vals['distance'] > maxi:
                                    vals['force_color'] = "#FF0000"
                                    vals['name'] = "TROP LOIN"
                                    vals['disponible'] = False
                                # Créneau plus loin que la recherche accepte
                                elif mode_recherche == 'duree' and vals['duree'] > maxi:
                                    vals['force_color'] = "#FF0000"
                                    vals['name'] = "TROP LOIN"
                                    vals['disponible'] = False
                                # Trajet aller-retour plus long que la durée de l'intervention
                                elif vals['duree'] > duree_dispo * 60:
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


class OfTourneeRdvLine(models.TransientModel):
    _name = 'of.tournee.rdv.line'
    _description = 'Propositions des RDVs'
    _order = "date, employee_id, date_flo"
    _inherit = "of.calendar.mixin"

    date = fields.Date(string="Date")
    debut_dt = fields.Datetime(string=u"Début")
    fin_dt = fields.Datetime(string="Fin")
    date_flo = fields.Float(string='Date', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    description = fields.Char(string=u"Créneau", size=128)
    wizard_id = fields.Many2one('of.tournee.rdv', string="RDV", required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Intervenant')
    intervention_id = fields.Many2one('of.planning.intervention', string="Planning")
    name = fields.Char(string="name", default="DISPONIBLE")
    distance = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    dist_prec = fields.Float(string='Dist.Prec. (km)', digits=(12, 0))
    dist_suiv = fields.Float(string='Dist.Suiv. (km)', digits=(12, 0))
    dist_ortho = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    dist_ortho_prec = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    dist_ortho_suiv = fields.Float(string='Dist.tot. (km)', digits=(12, 0), help="distance prec + distance suiv")
    duree = fields.Float(string=u'Durée.tot. (min)', default=-1, digits=(12, 0), help=u"durée prec + durée suiv")
    duree_prec = fields.Float(string=u'Durée.Prec. (min)', digits=(12, 0))
    duree_suiv = fields.Float(string=u'Durée.Suiv. (min)', digits=(12, 0))
    of_color_ft = fields.Char(related="employee_id.of_color_ft", readonly=True)
    of_color_bg = fields.Char(related="employee_id.of_color_bg", readonly=True)
    disponible = fields.Boolean(string="Est dispo", default=True)
    force_color = fields.Char("Couleur")
    allday = fields.Boolean('All Day', default=False)
    selected = fields.Boolean(u'Créneau sélectionné', default=False)
    selected_hour = fields.Float(string='Heure du RDV', digits=(2, 2))
    selected_description = fields.Html(string="Description", related="wizard_id.description")

    geo_lat = fields.Float(
        string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", compute="_compute_geo",
        readonly=True)
    geo_lng = fields.Float(
        string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", compute="_compute_geo",
        readonly=True)
    precision = fields.Selection(
        GEO_PRECISION, default='not_tried', readonly=True, compute="_compute_geo",
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")

    # @api.depends

    @api.multi
    @api.depends("intervention_id")
    def _compute_geo(self):
        for line in self:
            if line.intervention_id:
                # Créneau déjà occupé
                vals = {
                    'geo_lat': line.intervention_id.geo_lat,
                    'geo_lng': line.intervention_id.geo_lng,
                    'precision': line.intervention_id.precision,
                }
            else:
                # Créneau libre
                vals = {
                    'geo_lat': line.wizard_id.geo_lat,
                    'geo_lng': line.wizard_id.geo_lng,
                    'precision': line.wizard_id.precision,
                }
            line.update(vals)

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

    # Actions

    @api.multi
    def button_confirm(self):
        """Sélectionne ce créneau en tant que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        d = fields.Date.from_string(self.date)
        date_propos_dt = datetime.combine(d, datetime.min.time()) + timedelta(hours=self.selected_hour)  # datetime local
        date_propos_dt = tz.localize(date_propos_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc
        self.wizard_id.date_propos = date_propos_dt
        return self.wizard_id.button_confirm()

    @api.multi
    def button_select(self):
        """Sélectionne ce créneau en tant que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        rdv_line_obj = self.env["of.tournee.rdv.line"]
        selected_line = rdv_line_obj.search([('wizard_id', '=', self.wizard_id.id), ('selected', '=', True)])
        selected_line.selected = False
        self.selected = True
        self.selected_hour = self.date_flo

        address = self.wizard_id.partner_address_id
        name = address.name or (address.parent_id and address.parent_id.name) or ''
        name += address.zip and (" " + address.zip) or ""
        name += address.city and (" " + address.city) or ""
        wizard_vals = {
            'date_display'    : self.date,
            'name'            : name,
            'employee_id'       : self.employee_id.id,
            'date_propos'     : self.debut_dt,
            'date_propos_hour': self.date_flo,
            'res_line_id'     : self.id,
        }
        self.wizard_id.write(wizard_vals)

        return {'type': 'ir.actions.do_nothing'}

    # Autres

    @api.model
    def get_nb_dispo(self, wizard):
        """Retourne le nombre de créneaux disponibles (qui correspondent aux critères de recherche),
            le nombre de créneaux trop éloignés, et le premier résultat (en fonction du critère de résultat)"""
        # ne pas inclure les lignes associées a une intervention ni les lignes de début et fin de recherche
        lines = self.search([('wizard_id', '=', wizard.id),
                             ('allday', '=', False),
                             ('intervention_id', '=', False)],
                            order="distance, debut_dt")  # events allDay sont debut et fin de recherche
        lines_dispo = self.search([('wizard_id', '=', wizard.id), ('disponible', '=', True)],
                                  order="distance, debut_dt")
        nb = len(lines)
        nb_dispo = len(lines_dispo)
        first_res = lines_dispo and lines_dispo[0] or lines and lines[0] or False
        return nb, nb_dispo, first_res

    @api.model
    def get_state_int_map(self):
        """de of.calendar.mixin"""
        v0 = {'label': 'Brouillon', 'value': 0}
        v1 = {'label': u'Confirmé', 'value': 1}
        v2 = {'label': u'Réalisé', 'value': 2}
        v3 = {'label': u'Disponibilité', 'value': 3}
        return v0, v1, v2, v3
