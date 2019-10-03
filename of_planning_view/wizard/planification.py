# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date
#import pytz
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
#import urllib
from math import asin, sin, cos, sqrt, radians
#import requests

"""ROUTING_BASE_URL = "http://s-hotel.openfire.fr:5000/"
ROUTING_VERSION = "v1"
ROUTING_PROFILE = "driving" """

def hours_to_strs(*hours):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return tuple("%02dh%02d" % (hour, round((hour % 1) * 60)) for hour in hours)

def voldwazo(lat1, lng1, lat2, lng2):
    u"""
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param *: Coordonnées gps en degrés
    """
    lat1, lng1, lat2, lng2 = [radians(v) for v in (lat1, lng1, lat2, lng2)]
    return 2*asin(sqrt((sin((lat1-lat2)/2)) ** 2 + cos(lat1)*cos(lat2)*(sin((lng1-lng2)/2)) ** 2)) * 6366

class OfPlanifCreneauProp(models.TransientModel):
    _name = 'of.planif.intervention'
    _description = u"Proposition d'intervention à programmer"
    _order = "priorite DESC"

    service_id = fields.Many2one("of.service", string="Service")
    creneau_id = fields.Many2one('of.planif.creneau', string=u"Créneau")

    partner_name = fields.Char(related='service_id.partner_id.name', readonly=True)
    partner_mobile = fields.Char(related='service_id.partner_id.mobile', readonly=True)
    tache_name = fields.Char(related='service_id.tache_id.name', readonly=True)
    address_zip = fields.Char('Code Postal', size=24, related='service_id.address_id.zip', readonly=True)
    address_city = fields.Char('Ville', related='service_id.address_id.city', readonly=True)
    geo_lat = fields.Float(related='service_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='service_id.geo_lng', readonly=True)
    precision = fields.Selection(related='service_id.precision', readonly=True)

    distance_dwazo_prec = fields.Float(string=u'Distance du précédent', digits=(5, 5), compute="_compute_distance_dwazo", help="À vol d'oiseau")
    distance_dwazo_suiv = fields.Float(string=u'Distance du suivant', digits=(5, 5), compute="_compute_distance_dwazo", help="À vol d'oiseau")

    dummy_field = fields.Boolean(string=u"A VER?", compute="_compute_dummy_field")
    priorite = fields.Integer(string=u"Priorité")

    @api.multi
    @api.depends('geo_lat', 'geo_lng', 'creneau_id.geo_lat_prec', 'creneau_id.geo_lng_prec', 
                 'creneau_id.geo_lat_suiv', 'creneau_id.geo_lng_suiv')
    def _compute_dummy_field(self):
        for a_planifier in self:
            a_planifier.dummy_field = True

    @api.multi
    @api.depends('geo_lat', 'geo_lng', 'creneau_id.geo_lat_prec', 'creneau_id.geo_lng_prec', 
                 'creneau_id.geo_lat_suiv', 'creneau_id.geo_lng_suiv')
    def _compute_distance_dwazo(self):
        for a_planifier in self:
            if a_planifier.geo_lat == 0.0 or a_planifier.geo_lng == 0.0:
                a_planifier.distance_dwazo_prec = -1
                a_planifier.distance_dwazo_suiv = -1
                continue
            if a_planifier.creneau_id.geo_lat_prec == 0.0 or a_planifier.creneau_id.geo_lng_prec == 0.0:
                a_planifier.distance_dwazo_prec = -1
            else:
                a_planifier.distance_dwazo_prec = voldwazo(a_planifier.geo_lat, a_planifier.geo_lng, a_planifier.creneau_id.geo_lat_prec, a_planifier.creneau_id.geo_lng_prec)
            if a_planifier.creneau_id.geo_lat_suiv == 0.0 or a_planifier.creneau_id.geo_lng_suiv == 0.0:
                a_planifier.distance_dwazo_suiv = -1
            else:
                a_planifier.distance_dwazo_suiv = voldwazo(a_planifier.geo_lat, a_planifier.geo_lng, a_planifier.creneau_id.geo_lat_suiv, a_planifier.creneau_id.geo_lng_suiv)

    """@api.model
    def get_candidats(self, date_creneau, duree_creneau, distance_max, address_prec_id, address_suiv_id):
        un_mois = timedelta(days=30)
        une_semaine = timedelta(days=7)
        date_creneau_da = fields.Date.from_string(self.date_creneau)
        date_un_mois_da = date_creneau_da + un_mois
        date_1_semaine_da = date_creneau_da + une_semaine  # pour les services recurrents
        date_2_semaines_da = date_creneau_da + 2 * une_semaine  # pour les services recurrents
        date_moins_un_mois_da = date_creneau_da - un_mois  # pour les services recurrents
        date_moins_3_semaines_da = date_creneau_da - 3 * une_semaine  # pour les services recurrents
        date_moins_2_semaines_da = date_creneau_da - 2 * une_semaine  # pour les services recurrents
        date_un_mois_str = fields.Date.to_string(date_un_mois_da)
        date_1_semaine_str = fields.Date.to_string(date_1_semaine_da)
        date_2_semaines_str = fields.Date.to_string(date_2_semaines_da)
        date_moins_un_mois_str = fields.Date.to_string(date_moins_un_mois_da)
        date_moins_3_semaines_str = fields.Date.to_string(date_moins_3_semaines_da)
        date_moins_2_semaines_str = fields.Date.to_string(date_moins_2_semaines_da)
        taches_possibles = self.env['of.planning.tache'].search([('duree', '<=', duree_creneau)])  # seulement les taches suffisamment courtes a prendre en compte
        vals_list = []
        # services
        services = self.env['of.service'].search([
            ('tache_id', 'in', taches_possibles._ids),
            ('date_next', '<=', date_un_mois_str),  # ne pas proposer d'interventions à programmer dans plus d'un mois
            '|',
            '&', ('recurrence', '=', True), '|', ('date_fin', '=', False), ('date_fin', '>', self.date_creneau)  # pour les service récurrents, la date de fin est la date de fin du contrat
            ('recurrence', '=', False),
            ])
        distance_max = self.distance_max * 1.3  # approximation

        for service in services:
            voldwazo_prec = voldwazo(service.geo_lat, service.geo_lng, address_prec_id.geo_lat, address_prec_id.geo_lng)
            voldwazo_suiv = voldwazo(service.geo_lat, service.geo_lng, address_suiv_id.geo_lat, address_suiv_id.geo_lng)
            priorite = 0
            if voldwazo_prec > distance_max:  # trop loins
                continue
            if voldwazo_suiv > distance_max:
                continue
            if voldwazo_prec + voldwazo_suiv <= 5:
                priorite += 3
            elif voldwazo_prec + voldwazo_suiv <= 10:
                priorite += 2
            elif voldwazo_prec + voldwazo_suiv <= 15:
                priorite += 1
            if service.recurrence and (not service.date_fin or service.date_fin > date_un_mois_str):  # service recurrent sans date de fin ou qui termine dans + d'un mois
                # on prend en compte la date de prochaine intervention
                if service.date_next <= date_moins_un_mois_str:  # date de prochaine intervention il y a plus d'un mois: en retard!
                    priorite += 3
                elif service.date_next <= date_moins_3_semaines_str:  # date de prochaine intervention il y a plus de 3 semaines: à faire cette semaine
                    priorite += 2
                elif service.date_next <= date_moins_2_semaines_str:  # date de prochaine intervention il y a plus de 2 semaines: à faire cette quinzaine
                    priorite += 1
            # pas besoin de gérer le cas service récurrent déjà terminé grace au search plus haut
            else:
                # on prend en compte la date de fin
                if service.date_fin < self.date_creneau:  # en retard!
                    priorite += 3
                elif service.date_fin <= date_1_semaine_str: # à faire cette semaine
                    priorite += 2
                elif service.date_fin <= date_2_semaines_str: # à faire cette quinzaine
                    priorite += 1

            vals = {
                'priorite': priorite,
                'service_id': service.id,
            }
            vals_list.append(vals)

        return vals_list

    @api.model
    def peupler_candidats(self, date_creneau, duree_creneau, distance_max, address_prec_id, address_suiv_id):
        vals_list = self.get_candidats(date_creneau, duree_creneau, distance_max, address_prec_id, address_suiv_id)
        la_list = [(5, 0, 0)] + [(0, 0, values) for values in vals_list]

        self.proposition_ids = la_list"""


class OfPlanifCreneau(models.TransientModel):
    _name = 'of.planif.creneau'
    _description = u'Prise de RDV depuis un créneau disponible'
    """
    @api.model
    def _default_partner(self):
        # Suivant que la prise de rdv se fait depuis la fiche client ou un service
        if self._context.get('active_model', '') == 'res.partner':
            partner_id = self._context['active_ids'][0]
        elif self._context.get('active_model', '') == 'of.service':
            partner_id = self.env['of.service'].browse(self._context['active_ids'][0]).partner_id.id
        else:
            return False

        partner = self.env['res.partner'].browse(partner_id)
        while partner.parent_id:
            partner = partner.parent_id
        return partner

    @api.model
    def _default_service(self):
        active_model = self._context.get('active_model', '')
        service = False
        if active_model == "of.service":
            service_id = self._context['active_ids'][0]
            service = self.env["of.service"].browse(service_id)
        elif active_model == "res.partner":
            partner = self._default_partner()
            if partner:
                service = self.env['of.service'].search([('partner_id', '=', partner.id)], limit=1)
        return service

    @api.model
    def _default_address(self):
        partner_obj = self.env['res.partner']
        active_model = self._context.get('active_model', '')
        if active_model == "of.service":
            service = self.env["of.service"].browse(self._context['active_ids'][0])
            partner = service.partner_id
            address = service.address_id
        elif active_model == "res.partner":
            partner = partner_obj.browse(self._context['active_ids'][0])
            address = partner_obj.browse(partner.address_get(['delivery'])['delivery'])

        if address and not (address.geo_lat or address.geo_lng):
            address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
                                          '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)],
                                         limit=1) or address
        return address or False
    """
    date_creneau = fields.Date(string="Date du créneau")
    heure_debut_creneau = fields.Float(string=u'Heude de début', digits=(5, 5))
    heure_fin_creneau = fields.Float(string=u'Heude de fin', digits=(5, 5))
    distance_max = fields.Integer("Distance max.",default=30)
    duree_creneau = fields.Float(string=u"Durée")#, compute="_compute_duree_creneau")
    employee_id = fields.Many2one('hr.employee', string="Intervenant")
    # lieu précédent
    lieu_prec_id = fields.Many2one("res.partner", string="lieu précédent")
    geo_lat_prec = fields.Float(related='lieu_prec_id.geo_lat', readonly=True)
    geo_lng_prec = fields.Float(related='lieu_prec_id.geo_lng', readonly=True)
    precision_prec = fields.Selection(related='lieu_prec_id.precision', readonly=True)
    # lieu suivant
    lieu_suiv_id = fields.Many2one("res.partner", string="lieu suivant")
    geo_lat_suiv = fields.Float(related='lieu_suiv_id.geo_lat', readonly=True)
    geo_lng_suiv = fields.Float(related='lieu_suiv_id.geo_lng', readonly=True)
    precision_suiv = fields.Selection(related='lieu_suiv_id.precision', readonly=True)
    secteur_id = fields.Many2one('of.secteur', string="Secteur", help="laisser vide pour ne pas restreindre à un secteur en particulier")

    proposition_ids = fields.One2many('of.planif.intervention', 'creneau_id', string="propositions")#, compute="peupler_candidats")

    @api.onchange("distance_max")
    def onchange_distance_max(self):
        # lancer l'auto-search
        self.compute()
        #self.peupler_candidats()

    @api.multi
    def compute(self):
        self.ensure_one()

    @api.multi
    def get_candidats(self):
        self.ensure_one()
        un_mois = timedelta(days=30)
        une_semaine = timedelta(days=7)
        date_creneau_da = fields.Date.from_string(self.date_creneau)
        date_un_mois_da = date_creneau_da + un_mois
        date_1_semaine_da = date_creneau_da + une_semaine  # pour les services recurrents
        date_2_semaines_da = date_creneau_da + 2 * une_semaine  # pour les services recurrents
        date_moins_un_mois_da = date_creneau_da - un_mois  # pour les services recurrents
        date_moins_3_semaines_da = date_creneau_da - 3 * une_semaine  # pour les services recurrents
        date_moins_2_semaines_da = date_creneau_da - 2 * une_semaine  # pour les services recurrents
        date_un_mois_str = fields.Date.to_string(date_un_mois_da)
        date_1_semaine_str = fields.Date.to_string(date_1_semaine_da)
        date_2_semaines_str = fields.Date.to_string(date_2_semaines_da)
        date_moins_un_mois_str = fields.Date.to_string(date_moins_un_mois_da)
        date_moins_3_semaines_str = fields.Date.to_string(date_moins_3_semaines_da)
        date_moins_2_semaines_str = fields.Date.to_string(date_moins_2_semaines_da)
        taches_emp = self.employee_id.tache_ids
        taches_possibles = taches_emp.filtered(lambda t: t.duree <= self.duree_creneau)  # seulement les taches suffisamment courtes a prendre en compte
        vals_list = []
        service_domain = [
            ('tache_id', 'in', taches_possibles.ids),
            ('date_next', '<=', date_un_mois_str),  # ne pas proposer d'interventions à programmer dans plus d'un mois
            '|',
            '&', ('recurrence', '=', True), '|', ('date_fin', '=', False), ('date_fin', '>', self.date_creneau),  # pour les service récurrents, la date de fin est la date de fin du contrat
            ('recurrence', '=', False),
        ]
        if self.secteur_id:
            service_domain.append(('secteur_tech_id', '=', self.secteur_id.id))
        # services
        services = self.env['of.service'].search()
        distance_max = self.distance_max * 1.3  # approximation

        for service in services:
            voldwazo_prec = voldwazo(service.geo_lat, service.geo_lng, self.lieu_prec_id.geo_lat, self.lieu_prec_id.geo_lng)
            voldwazo_suiv = voldwazo(service.geo_lat, service.geo_lng, self.lieu_suiv_id.geo_lat, self.lieu_suiv_id.geo_lng)
            priorite = 0
            if voldwazo_prec > distance_max:  # trop loins
                continue
            if voldwazo_suiv > distance_max:
                continue
            if voldwazo_prec + voldwazo_suiv <= 5:
                priorite += 3
            elif voldwazo_prec + voldwazo_suiv <= 10:
                priorite += 2
            elif voldwazo_prec + voldwazo_suiv <= 15:
                priorite += 1
            if service.recurrence and (not service.date_fin or service.date_fin > date_un_mois_str):  # service recurrent sans date de fin ou qui termine dans + d'un mois
                # on prend en compte la date de prochaine intervention
                if service.date_next <= date_moins_un_mois_str:  # date de prochaine intervention il y a plus d'un mois: en retard!
                    priorite += 3
                elif service.date_next <= date_moins_3_semaines_str:  # date de prochaine intervention il y a plus de 3 semaines: à faire cette semaine
                    priorite += 2
                elif service.date_next <= date_moins_2_semaines_str:  # date de prochaine intervention il y a plus de 2 semaines: à faire cette quinzaine
                    priorite += 1
            # pas besoin de gérer le cas service récurrent déjà terminé grace au search plus haut
            else:
                # on prend en compte la date de fin
                if service.date_fin < self.date_creneau:  # en retard!
                    priorite += 3
                elif service.date_fin <= date_1_semaine_str: # à faire cette semaine
                    priorite += 2
                elif service.date_fin <= date_2_semaines_str: # à faire cette quinzaine
                    priorite += 1

            vals = {
                'priorite': priorite,
                'service_id': service.id,
            }
            vals_list.append(vals)

        return vals_list

    @api.model
    def peupler_candidats(self):
        self.ensure_one()
        vals_list = self.get_candidats()
        la_list = [(5, 0, 0)] + [(0, 0, values) for values in vals_list]

        self.proposition_ids = la_list

    @api.multi
    def button_dummy(self):
        self.peupler_candidats()
        return {'type': 'ir.actions.do_nothing'}

    """@api.multi
    @api.depends('heure_debut_creneau', 'heure_fin_creneau')
    def _compute_duree_creneau(self):
        for wizard in self:
            wizard.duree_creneau = wizard.heure_fin_creneau - wizard.heure_debut_creneau"""
