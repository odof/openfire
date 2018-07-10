# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date
import pytz
import math
from math import cos
from odoo.addons.of_planning_tournee.models.of_planning_tournee import distance_points
from odoo.exceptions import UserError


NEW_RES_MODES = [
    ('distance_top_view', u"Distance à vol d'oiseau"),
    ('distance_by_road', u"Distance à parcourir"),
    ('time_by_road', u'Temps de trajet'),
]

EPICENTERS = [
    ('team_start_address', u"Adresse départ equipe"),
    ('company_address', u"Adresse société"),
    ('client_address', u'Adresse client'),
]

class OfTourneeRdv2(models.TransientModel):
    _name = 'of.tournee.rdv2'
    _description = u'Prise de RDV dans les tournées (v2)'

    @api.model
    def _default_partner(self):
        partner_id = self._context.get('active_model', '') == 'res.partner' and self._context['active_ids'][0]
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            while partner.parent_id:
                partner = partner.parent_id
            return partner
        return False

    @api.model
    def _default_service(self):
        service_obj = self.env['of.service']
        partner = self._default_partner()
        if not partner:
            return False
        services = service_obj.search([('partner_id', '=', partner.id)], limit=1)
        return services

    @api.model
    def _default_address(self):
        partner_obj = self.env['res.partner']

        partner = self._default_partner()
        if partner and partner.id != self._context['active_ids'][0]:
            # La fonction est appelée à partir d'une adresse
            return partner_obj.browse(self._context['active_ids'][0])

        address_id = partner.address_get(['delivery'])['delivery']
        if address_id:
            address = partner_obj.browse(address_id)
            if not (address.geo_lat or address.geo_lng):
                address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id),
                                              '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)], limit=1)
                if not address:
                    address = partner_obj.search(['|', ('id', '=', partner.id), ('parent_id', '=', partner.id)])
        return address_id


    # Commons fields to of.tournne.rdv
    description = fields.Text(string='Description')
    tache_id = fields.Many2one('of.planning.tache', string='Prestation', required=True)
    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe")
    equipe_id_pre = fields.Many2one('of.planning.equipe', string=u'Équipe', domain="[('tache_ids','in',tache_id)]")
    duree = fields.Float(string=u'Durée', required=True, digits=(12, 5))
    planning_ids = fields.One2many('of.tournee.rdv.line2', 'wizard_id', string='Proposition de RDVs')
    partner_id = fields.Many2one('res.partner', string='Client', required=True, readonly=True, default=_default_partner)
    partner_address_id = fields.Many2one('res.partner', string="Adresse d'intervention", required=True, default=_default_address,
                                         domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    service_id = fields.Many2one('of.service', string='Service client', default=_default_service, domain="[('partner_id', '=', partner_id)]")

    # New fields (only of.tourner.rdv2)
    mode2 = fields.Selection(NEW_RES_MODES, string=u"Mode", required=True, default="distance_top_view")
    date_recherche_debut = fields.Date(string=u"Date debut", required=True, default=lambda *a: (date.today()).strftime('%Y-%m-%d'))
    date_recherche_fin = fields.Date(string=u'Date fin', required=True, default=lambda *a: (date.today() + timedelta(days=15)).strftime('%Y-%m-%d'))
    distance2 = fields.Float(string=u'Distance', digits=(8, 2), required=True, default=10, help=u'Éloignement maximum (km)')
    time2 = fields.Float(string=u"Temps", required=True, default=10, help=u"Temps maximum par route")
    epicenter = fields.Selection(EPICENTERS, string=u"Épicentre", required=True, default="team_start_address")
    epi_lat = fields.Float(string='Épi Lat', digits=(8, 8))
    epi_lng = fields.Float(string='Épi Lng', digits=(8, 8))
    epi_client = fields.Char(string=u"Épicentre client")
    client_id = fields.Many2one('res.partner', string='Client', default=_default_partner)

    @api.onchange('epicenter', 'equipe_id_pre', 'client_id')
    def _onchange_epi_address(self):
        if self.epicenter == 'team_start_address':
            if self.equipe_id_pre:
                if self.equipe_id_pre.address_id.geo_lat and self.equipe_id_pre.address_id.geo_lng:
                    self.epi_lat = self.equipe_id_pre.address_id.geo_lat
                    self.epi_lng = self.equipe_id_pre.address_id.geo_lng
                else:
                    raise UserError(u"L'équipe sélectionnée n'a pas de coordonnées GPS")
        if self.epicenter == 'company_address':
            if self.partner_id.company_id.geo_lat and self.partner_id.company_id.geo_lng:
                self.epi_lat = self.partner_id.company_id.geo_lat
                self.epi_lng = self.partner_id.company_id.geo_lng
            else:
                raise UserError(u"La société n'a pas de coordonnées GPS")
        if self.epicenter == 'client_address':
            if self.client_id.geo_lat and self.client_id.geo_lng:
                self.epi_lat = self.client_id.geo_lat
                self.epi_lng = self.client_id.geo_lng
            else:
                raise UserError(u"Ce client n'a pas n'a pas de coordonnées GPS")
        if self.epicenter == 'manual':
            pass
        

    
    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        service_obj = self.env['of.service']
        services = False
        if self.tache_id:
            if self.service_id:
                if self.service_id.tache_id.id == self.tache_id.id:
                    services = True
                else:
                    services = service_obj.search([('partner_id', '=', self.partner_id.id),('tache_id', '=', self.tache_id.id)], limit=1)
                    if services:
                        self.service_id = services

            if self.tache_id.duree:
                self.duree = self.tache_id.duree

            if self.equipe_id_pre not in self.tache_id.equipe_ids:
                self.equipe_id_pre = False

        if not services:
            self.service_ids = False


    @api.multi
    def _get_equipe_possible(self):
        self.ensure_one()
        equipe_ids = []
        for planning in self.planning_ids:
            if planning.equipe_id.id not in equipe_ids:
                equipe_ids.append(planning.equipe_id.id)
        return equipe_ids








class OfTourneeRdvLine2(models.TransientModel):
    _name = 'of.tournee.rdv.line2'
    _description = u"Propositions des RDVs (v2)"


    @api.depends()
    def _calc_distances(self):
        jours_res = {}
        for line in self:
            jours_res.setdefault(line.wizard_id, {}).setdefault(line.equipe_id, []).append(line)

        for wizard, equipes in jours_res.iteritems():
            partner_address = wizard.partner_address_id
            for equipe, lines in equipes.iteritems():
                lines_libres = []
                last_gps = (equipe.address_id.geo_lat, equipe.address_id.geo_lng)
                next_gps = False
                lines.sort(key=lambda p: p.date_flo)
                for line in lines+[False]:
                    if line is False:
                        address = equipe.address_id
                        next_gps = (address.geo_lat, address.geo_lng)
                    elif line.intervention_id:
                        address = line.intervention_id.address_id
                        next_gps = (address.geo_lat, address.geo_lng)

                        line.distance = ''
                        line.dist_prec = ''
                        line.dist_suiv = ''
                    else:
                        lines_libres.append(line)

                    if next_gps:
                        for line in lines_libres:
                            erreur = False
                            dist_tot = 0
                            vals = []
                            for gps in (last_gps, next_gps):
                                if gps[0]:
                                    dist = distance_points(gps[0], gps[1], partner_address.geo_lat, partner_address.geo_lng)
                                    dist_tot += dist
                                    vals.append("%0.2f" % dist)
                                else:
                                    vals.append('?')
                                    erreur = '?'

                            line.distance = erreur or "%0.2f" % dist_tot
                            line.dist_prec = vals[0]
                            line.dist_suiv = vals[1]
                        lines_libres = []
                        last_gps = next_gps
                        next_gps = False

    date_flo = fields.Float(string='Date', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    description = fields.Char(string='RDV', size=128)
    wizard_id = fields.Many2one('of.tournee.rdv2', string="RDV", required=True, ondelete='cascade')
    equipe_id = fields.Many2one('of.planning.equipe', string='Equipe')
    intervention_id = fields.Many2one('of.planning.intervention', string="Planning")

    distance = fields.Char(compute="_calc_distances", string='Dist.tot.')
    dist_prec = fields.Char(compute="_calc_distances", string='Dist.Prec.')
    dist_suiv = fields.Char(compute="_calc_distances", string='Dist.Suiv')

    _order = "date_flo"
    
    

