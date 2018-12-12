# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import ValidationError

import math
from math import asin, sin, cos, sqrt

def distance_points(lat1, lon1, lat2, lon2):
    u"""
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param *: Coordonnées gps en degrés
    """
    lat1, lon1, lat2, lon2 = [math.radians(v) for v in (lat1, lon1, lat2, lon2)]
    return 2*asin(sqrt((sin((lat1-lat2)/2)) ** 2 + cos(lat1)*cos(lat2)*(sin((lon1-lon2)/2)) ** 2)) * 6366

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    tournee_id = fields.Many2one('of.planning.tournee', compute='_compute_tournee_id', store=True, string='Planification')
    partner_city = fields.Char(related='address_id.city', store=True)

    @api.multi
    @api.depends('equipe_id', 'date', 'tournee_id.date', 'tournee_id.equipe_id')
    def _compute_tournee_id(self):
        tournee_obj = self.env['of.planning.tournee']
        for intervention in self:
            if intervention.equipe_id and intervention.date:
                tournee = tournee_obj.search([('equipe_id', '=', intervention.equipe_id.id), ('date', '=', intervention.date[:10])], limit=1)
                intervention.tournee_id = tournee

    @api.multi
    def create_tournee(self):
        self.ensure_one()
        tournee_obj = self.env['of.planning.tournee']
        # if self.tache_id.category_id.type_planning_intervention != 'tournee':
        #     return False
        date_intervention = self.date
        date_jour = isinstance(date_intervention, basestring) and date_intervention[:10] or date_intervention.strftime('%Y-%m-%d')
        address = self.address_id
        # ville = address.ville or address
        ville = address
        country = address.country_id
        tournee_data = {
            'date'       : date_jour,
            'equipe_id'  : self.equipe_id.id,
            'epi_lat'    : ville.geo_lat,
            'epi_lon'    : ville.geo_lng,
            'adr_id'     : address.id,
            # 'ville'      : address.ville and address.ville.id,
            'zip'        : ville.zip,
            'city'       : ville.city,
            'country_id' : country and country.id,
            'is_bloque'  : False,
            'is_confirme': False
        }
        return tournee_obj.create(tournee_data)

    @api.model
    def remove_tournee(self, date, equipe_id):
        date = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
        planning_intervention_ids = self.search([('date', '>=', date), ('date', '<=', date), ('equipe_id', '=', equipe_id)])
        if planning_intervention_ids:
            # Il existe encore des plannings pour la tournee, on ne la supprime pas
            return True

        planning_tournee_obj = self.env['of.planning.tournee']
        plannings_tournee = planning_tournee_obj.search([('date', '=', date), ('equipe_id', '=', equipe_id),
                                                         ('is_bloque', '=', False), ('is_confirme', '=', False)])
        plannings_tournee.unlink()

    @api.model
    def create(self, vals):
        planning_tournee_obj = self.env['of.planning.tournee']

        # On verifie que la tournee n'est pas deja complete ou bloquee
        date_jour = isinstance(vals['date'], basestring) and vals['date'][:10] or vals['date'].strftime('%Y-%m-%d')

        planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                            ('equipe_id', '=', vals['equipe_id']),
                                                            ('is_bloque', '=', True)])
        if planning_tournee_ids:
            raise ValidationError(u'La tournée de cette équipe est bloquée')

        intervention = super(OfPlanningIntervention, self).create(vals)
        planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                            ('equipe_id', '=', vals['equipe_id'])])
        if not planning_tournee_ids:
            intervention.create_tournee()
        return intervention

    @api.multi
    def write(self, vals):
        planning_tournee_obj = self.env['of.planning.tournee']

        interventions = []
        if 'date' in vals or 'equipe_id' in vals:
            for intervention in self:
                date = vals.get('date', intervention.date)
                equipe_id = vals.get('equipe_id', intervention.equipe_id.id)

                date_jour = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
                interventions.append((intervention, date_jour, equipe_id, intervention.date, intervention.equipe_id.id))
                planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                                    ('equipe_id', '=', equipe_id),
                                                                    ('is_bloque', '=', True)])
                if planning_tournee_ids:
                    raise ValidationError(u'La tournée de cette équipe est bloquée')
        super(OfPlanningIntervention, self).write(vals)

        for intervention, date_jour, equipe_id, date_prec, equipe_prec in interventions:
            planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour), ('equipe_id', '=', equipe_id)])
            if not planning_tournee_ids:
                intervention.create_tournee()
            self.remove_tournee(date_prec, equipe_prec)
        return True

    @api.multi
    def unlink(self):
        interventions = []
        for intervention in self:
            date = intervention.date
            date_jour = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
            interventions.append((date_jour, intervention.equipe_id.id))
        super(OfPlanningIntervention, self).unlink()
        for date, equipe_id in interventions:
            self.remove_tournee(date, equipe_id)
        return True

    @api.multi
    def _calc_new_description(self):
        self.ensure_one()

        tache = self.tache_id
        for service in self.address_id.service_address_ids:
            if service.tache_id == tache:
                infos = (
                    self.description,
                    tache.name,
                    # service.template_id and service.template_id.name,
                    service.note
                )
                res = [info for info in infos if info]
                self.description = "\n".join(res)

    @api.onchange('address_id')
    def _onchange_address_id(self):
        super(OfPlanningIntervention, self)._onchange_address_id()
        if self.address_id and self.tache_id:
            self._calc_new_description()

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        super(OfPlanningIntervention, self)._onchange_tache_id()
        if self.partner_id and self.tache_id:
            self._calc_new_description()


class OfPlanningEquipe(models.Model):
    _inherit = "of.planning.equipe"

    address_id = fields.Many2one('res.partner', string=u'Adresse de départ')
    address_retour_id = fields.Many2one('res.partner', string='Adresse de retour')
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        if self.employee_ids:
            self.address_id = self.employee_ids[0].address_home_id
            self.address_retour_id = self.address_id

    @api.onchange('address_id')
    def _onchange_address_id(self):
        if self.address_id:
            self.address_retour_id = self.address_id

class OfPlanningTournee(models.Model):
    _name = "of.planning.tournee"
    _description = "Tournée"
    _order = 'date DESC'
    _rec_name = 'date'

    _sql_constraints = [
        ('date_equipe_uniq', 'unique (date,equipe_id)', u"Il ne peut exister qu'une tournée par équipe pour un jour donné")
    ]

    date = fields.Date(string='Date', required=True)
    date_jour = fields.Char(compute="_compute_date_jour", string="Jour")
    equipe_id = fields.Many2one('of.planning.equipe', string=u'Équipe', required=True)
    epi_lat = fields.Float(string=u'Épicentre Lat', digits=(12, 12), required=True)
    epi_lon = fields.Float(string=u'Épicentre Lon', digits=(12, 12), required=True)
    address_depart_id = fields.Many2one('res.partner', string='Adresse départ')
    address_retour_id = fields.Many2one('res.partner', string='Adresse retour')

    zip_id = fields.Many2one('res.better.zip', 'Ville')
    distance = fields.Float(string='Eloignement (km)', digits=(12, 4), required=True, default=20.0)
    is_complet = fields.Boolean(compute="_compute_is_complet", string='Complet', store=True)
    is_bloque = fields.Boolean(string=u'Bloqué', help=u'Journée bloquée : ne sera pas proposée à la planification')
    is_confirme = fields.Boolean(string=u'Confirmé', default=True, help=u'Une tournée non confirmée sera supprimée si on lui retire ses rendez-vous')
    date_min = fields.Date(related="date", string="Date min")
    date_max = fields.Date(related="date", string="Date max")

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
    @api.depends('equipe_id', 'date', 'is_bloque',
                 'equipe_id.hor_md', 'equipe_id.hor_mf', 'equipe_id.hor_ad', 'equipe_id.hor_af')
    def _compute_is_complet(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        intervention_obj = self.env['of.planning.intervention']
        for tournee in self:
            if tournee.is_bloque:
                tournee.is_complet = False
                continue

            equipe = tournee.equipe_id

            interventions = intervention_obj.search([
                ('equipe_id', '=', equipe.id),
                ('date', '<=', tournee.date),
                ('date_deadline', '>=', tournee.date),
                ('state', 'in', ('draft', 'confirm'))
            ], order="date")
            if not interventions:
                tournee.is_complet = False
                continue

            date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(tournee.date))
            start_end_list = [
                (0, equipe.hor_md),
                (equipe.hor_mf, equipe.hor_ad),
                (equipe.hor_af, 24)
            ]

            for intervention in interventions:
                start_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date))
                if start_local.day != date_local.day:
                    start_flo = equipe.hor_md
                else:
                    start_flo = (start_local.hour +
                                 start_local.minute / 60 +
                                 start_local.second / 3600)

                end_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date_deadline))
                if end_local.day != date_local.day:
                    end_flo = equipe.hor_af
                else:
                    end_flo = (start_local.hour +
                               start_local.minute / 60 +
                               start_local.second / 3600)

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
    def _get_dummy_fields(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for tournee in self:
            d = fields.Date.context_today(self)
            tournee.date_min = d
            tournee.date_max = d

    @api.onchange('zip_id')
    def _onchange_zip_id(self):
        if self.zip_id:
            self.epi_lat = self.zip_id.geo_lat
            self.epi_lon = self.zip_id.geo_lng

    @api.onchange('equipe_id')
    def _onchange_equipe_id(self):
        if self.equipe_id:
            self.address_depart_id = self.equipe_id.address_id
            self.address_retour_id = self.equipe_id.address_retour_id

    @api.onchange('address_depart_id')
    def _onchange_address_depart_id(self):
        if self.address_depart_id:
            self.address_retour_id = self.address_depart_id

    @api.model
    def create(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        if vals.get('is_bloque'):
            if intervention_obj.search([('date', '>=', vals['date']), ('date', '<=', vals['date']),
                                        ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                        ('equipe_id', '=', vals['equipe_id'])]):
                raise ValidationError(u'Il existe déjà les interventions dans la journée de cette équipe')
        return super(OfPlanningTournee, self).create(vals)

    @api.multi
    def write(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        for tournee in self:
            if vals.get('is_bloque', tournee.is_bloque):
                date_intervention = vals.get('date', tournee.date)
                equipe_id = vals.get('equipe_id', tournee.equipe_id.id)
                if intervention_obj.search([('date', '>=', date_intervention), ('date', '<=', date_intervention),
                                            ('state', 'in', ('draft', 'confirm', 'done', 'unfinished')),
                                            ('equipe_id', '=', equipe_id)]):
                    raise ValidationError(u'Il existe déjà les interventions dans la journée de cette équipe')
        return super(OfPlanningTournee, self).write(vals)

    @api.multi
    def open_planification(self):
        self.ensure_one()
        plan_obj = self.env['of.tournee.planification']

        planif = plan_obj.create({
            'tournee_id'       : self.id,
            'distance_add'     : self.distance + 10.0,
            'plan_partner_ids' : plan_obj._get_partner_ids(self),
            'plan_planning_ids': plan_obj._get_planning_ids(self),
        })
        return planif._get_show_action()

class OfService(models.Model):
    _inherit = 'of.service'

    def _get_color(self):
        u""" COULEURS :
        gris : Service dont l'adresse n'a pas de coordonnées GPS
        rouge : Service dont la date de dernière intervention est inférieure à la date courante (ou à self._context.get('date_next_max'))
        bleu : Service dont le dernier rendez-vous est planifié hors tournée
        noir : Autres services
        """
        date_next_max = self._context.get('date_next_max') or fields.Date.today()

        for service in self:
            if not (service.address_id.geo_lat or service.address_id.geo_lng):
                service.color = 'gray'
            elif service.date_next <= date_next_max:
                service.color = 'red'
            elif service.planning_ids and not service.planning_ids[0].tournee_id:
                service.color = 'blue'
            else:
                service.color = 'black'
