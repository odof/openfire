# -*- encoding: utf-8 -*-

try:
    import json
except ImportError:
    json = None

try:
    import urllib
except ImportError:
    urllib = None

try:
    import requests
except ImportError:
    requests = None

import urllib3
from odoo import api, models, fields
from datetime import datetime, timedelta, date as d_date
import pytz
import math
from math import cos
from odoo.addons.of_planning_tournee.models.of_planning_tournee import distance_points
from odoo.exceptions import UserError

SEARCH_MODES = [
    ('distance', u'Distance (km)'),
    ('duree', u'Durée (min)'),
]

PICK_MODES = [
    ('date', u'Au plus tôt'),
    ('distance', u'Au plus proche'),
]

def hours_to_strs(*hours):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return tuple("%02dh%02d" % (hour, round((hour % 1) * 60)) for hour in hours)

class OFRDVCommercial(models.TransientModel):
    _name = 'of.rdv.commercial'
    _description = u'Prise de RDV commercial'

    @api.model
    def _default_partner(self): ###a verif
        active_model = self._context.get('active_model', '')
        partner_id = False
        if active_model == "res.partner":
            partner_id = self._context['active_ids'][0]
        elif active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
            partner_id = lead.partner_id.id

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            while partner.parent_id:
                partner = partner.parent_id
            return partner
        return False

    @api.model
    def _default_lead(self): ###a verif
        active_model = self._context.get('active_model', '')
        lead = False
        if active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
        return lead

    @api.model
    def _default_commercial(self): ###a verif
        active_model = self._context.get('active_model', '')
        if active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
            commercial = lead.user_id
            return commercial
        elif active_model == "res.partner":
            partner_id = self._context['active_ids'][0]
            partner = self.env['res.partner'].browse(partner_id)
            while partner.parent_id and not partner.user_id:
                partner = partner.parent_id
            commercial = partner.user_id
            return commercial
        else:
            return False

    @api.model
    def _default_address(self): ###a verif
        partner_obj = self.env['res.partner']
        active_model = self._context.get('active_model', '')
        if active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
            address_id = lead.partner_id.id
        elif active_model == "res.partner":
            partner = partner_obj.browse(self._context['active_ids'][0])
            address_id = partner.address_get(['delivery'])['delivery']

        if address_id:
            address = partner_obj.browse(address_id)
            if not (address.geo_lat or address.geo_lng):
                address = partner_obj.search(['|', ('id', '=', address.id), ('parent_id', '=', address.id),
                                              '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)], limit=1)
                if not address:
                    address = partner_obj.search(['|', ('id', '=', address.id), ('parent_id', '=', address.id)], limit=1)
            return address
        return False

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    name = fields.Char(string=u'Libellé', size=64, required=False)
    description = fields.Text(string='Description')
    user_id = fields.Many2one('res.users', string=u"Commercial", required=True, default=_default_commercial)
    duree = fields.Float(string=u'Durée', required=True, digits=(12, 2),default=0.25)
    creneau_ids = fields.One2many('of.rdv.commercial.line', 'wizard_id', string='Proposition de RDVs')
    date_propos = fields.Datetime(string=u'RDV Début')
    date_propos_hour = fields.Float(string=u'Heude de début', digits=(12, 5))
    date_recherche_debut = fields.Date(string='À partir du', required=True, default=lambda *a: (d_date.today() + timedelta(days=1)).strftime('%Y-%m-%d'))
    date_recherche_fin = fields.Date(string="Jusqu'au", required=True, default=lambda *a: (d_date.today() + timedelta(days=7)).strftime('%Y-%m-%d'))
    partner_id = fields.Many2one('res.partner', string='Client', required=True, readonly=True, default=_default_partner)
    rdv_address_id = fields.Many2one('res.partner', string="Adresse du RDV", default=_default_address,
                                         domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    date_display = fields.Char(string='Jour du RDV', size=64, readonly=True)
    lead_id = fields.Many2one('crm.lead', string='Opportunité', default=_default_lead, domain="[('partner_id', '=', partner_id)]")
    mode_recherche = fields.Selection(SEARCH_MODES, string="Mode de recherche", required=True, default="distance")
    mode_result = fields.Selection(PICK_MODES, string="Choix de la proposition", required=True, default="distance")
    max_recherche = fields.Float(string="Maximum")
    allday = fields.Boolean('All Day', default=False)
    hor_md = fields.Float(string=u'Matin début', required=True, digits=(12, 1),default=9) #TODO onchange user_id
    hor_mf = fields.Float(string='Matin fin', required=True, digits=(12, 1),default=12)
    hor_ad = fields.Float(string=u'Après-midi début', required=True, digits=(12, 1),default=14)
    hor_af = fields.Float(string=u'Après-midi fin', required=True, digits=(12, 1),default=18)
    jour_ids = fields.Many2many('of.jours', 'rdvcom_jours', 'rdvcom_id', 'jour_id', string='Jours travillés', required=True, default=_get_default_jours)

    zero_result = fields.Boolean(string="Recherche infructueuse",default=False,help="Aucun résultat")
    zero_dispo = fields.Boolean(string="Recherche infructueuse",default=False,help="Aucun résultat sufisament proche")
    display_search = fields.Boolean(string=u"Voir critères de recherche",default=True)
    display_res = fields.Boolean(string=u"Voir Résultats",default=False)
    res_line_id = fields.Many2one("of.rdv.commercial.line",string="Créneau Sélectionné")

    # champs ajoutés pour la vue map
    geo_lat = fields.Float(related='rdv_address_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='rdv_address_id.geo_lng', readonly=True)
    precision = fields.Selection(related='rdv_address_id.precision', readonly=True)
    partner_name = fields.Char(related='partner_id.name')
    ignorer_geo = fields.Boolean(u"Ignorer données géographiques")

    @api.onchange('mode_result')
    def _onchange_mode_result(self): ###a verif
        u"""Sélectionne le résultat en fonction du mode de résultat (au plus proche ou au plus tôt)"""
        self.ensure_one()
        if not (self.creneau_ids and self.display_search):
            return
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        if self.mode_result == "distance":
            le_order = "distance,debut_dt"
        else:
            le_order = "debut_dt,distance"
        # ne pas inclure les lignes associées a une intervention ni les lignes de début et fin de recherche
        lines = self.creneau_ids.search([('virtuel', '=', False),('calendar_id', '=', False)],order=le_order)
        lines_dispo = self.creneau_ids.search([('disponible', '=', True)],order=le_order)
        nb = len(lines)
        nb_dispo = len(lines_dispo)
        first_res = lines_dispo and lines_dispo[0] or lines and lines[0] or False
        vals ={}
        if first_res and first_res.id != self.res_line_id.id:
            address = self.rdv_address_id
            name = address.name or (address.parent_id and address.parent_id.name) or ''
            name += address.zip and (" " + address.zip) or ""
            name += address.city and (" " + address.city) or ""

            d_first_res = fields.Date.from_string(first_res.date)
            dt_propos = datetime.combine(d_first_res, datetime.min.time()) + timedelta(hours=first_res.date_flo)
            dt_propos = tz.localize(dt_propos, is_dst=None).astimezone(pytz.utc)

            vals = {
                'res_line_id'     : first_res.id,
                'date_display'    : first_res.date,
                'name'            : name,
                'user_id'         : first_res.user_id.id,
                'date_propos'     : dt_propos,
                'date_propos_hour': first_res.date_flo,
                'zero_result'     : False,
                'zero_dispo'      : nb_dispo == 0,
            }

            self.res_line_id.selected = False
            self.update(vals)
            self.res_line_id.selected = True

    @api.onchange('mode_recherche')
    def _onchange_mode_recherche(self):
        self.ensure_one()
        if self.mode_recherche and self.mode_recherche == u"distance":
            self.max_recherche = 50
        elif self.mode_recherche:
            self.max_recherche = 60

    @api.onchange('date_recherche_debut')
    def _onchange_date_recherche_debut(self):
        self.ensure_one()
        if self.date_recherche_debut:
            d_drd = fields.Date.from_string(self.date_recherche_debut)
            d_drf = d_drd + timedelta(days=6)
            self.date_recherche_fin = fields.Date.to_string(d_drf)

    @api.onchange('date_recherche_fin')
    def _onchange_date_recherche_fin(self):
        self.ensure_one()
        if self.date_recherche_fin and self.date_recherche_fin < self.date_recherche_debut:
            raise UserError(u"La date de fin de recherche doit être postérieure à la date de début de recherche")

    """
    a voir si réimplémenter cette fonctionnalité
    # Note: Séparation en 3 fonctions car, avec une seule fonction button_calcul(self, creneau_suivant=False),
    #       Odoo place le contexte dans cette variable si elle n'est pas fournie en paramètre ...
    @api.multi
    def button_calcul_suivant(self):
        # Calcule a prochaine intervention à partir de la dernière intervention proposée
        self.compute(creneau_suivant=True)
        context = dict(self._context, equipe_domain=self._get_equipe_possible())
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.tournee.rdv',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': context,
        }"""

    @api.multi
    def button_calcul(self):
        # Calcule a prochaine intervention à partir du lendemain de la date courante
        self.compute()
        context = dict(self._context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.rdv.commercial',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': context,
        }

    @api.multi
    def compute(self):
        u"""Calcul des prochains créneaux disponibles
        NOTE : Si un service est sélectionné incluant le samedi et/ou le dimanche,
               ceux-cis seront traités comme des jours normaux du point de vue des équipes
        """
        #TODO: finir de commenter
        self.ensure_one()

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        wizard_line_obj = self.env['of.rdv.commercial.line']
        calendar_obj = self.env['calendar.event']

        address = self.rdv_address_id
        jours = [jour.numero for jour in self.jour_ids] if self.jour_ids else range(1, 6)

        # Suppression des anciens créneaux
        creneau_del_ids = wizard_line_obj.search([])#[('wizard_id', '=', self.id)])
        if creneau_del_ids:
            creneau_del_ids.unlink()

        un_jour = timedelta(days=1)

        d_avant_recherche = fields.Date.from_string(self.date_recherche_debut) - un_jour
        avant_recherche = fields.Date.to_string(d_avant_recherche)
        dt_avant_recherche_debut = tz.localize(datetime.strptime(avant_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S")) # local datetime
        dt_avant_recherche_fin = tz.localize(datetime.strptime(avant_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S")) # local datetime
        d_apres_recherche = fields.Date.from_string(self.date_recherche_fin) + un_jour
        apres_recherche = fields.Date.to_string(d_apres_recherche)
        dt_apres_recherche_debut = tz.localize(datetime.strptime(apres_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S")) # local datetime
        dt_apres_recherche_fin = tz.localize(datetime.strptime(apres_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S")) # local datetime

        # Création des créneaux de début et fin de recherche
        wizard_line_obj.create({
            'name': 'Début de la recherche',
            'debut_dt': dt_avant_recherche_debut,
            'fin_dt': dt_avant_recherche_fin,
            'date_flo': 0.0,
            'date_flo_deadline': 23.9,
            'date': d_avant_recherche,
            'wizard_id': self.id,
            #'user_id': self.user_id.id,
            'user_partner_id': self.user_id.partner_id.id,
            'calendar_id': False,
            'disponible': False,
            'allday': True,
            'virtuel': True,
            'ignorer_geo': self.ignorer_geo,
        })
        wizard_line_obj.create({
            'name': 'Fin de la recherche',
            'debut_dt': dt_apres_recherche_debut,
            'fin_dt': dt_apres_recherche_fin,
            'date_flo': 0.0,
            'date_flo_deadline': 23.9,
            'date': d_apres_recherche,
            'wizard_id': self.id,
            #'user_id': self.user_id.id,
            'user_partner_id': self.user_id.partner_id.id,
            'calendar_id': False,
            'disponible': False,
            'allday': True,
            'virtuel': True,
            'ignorer_geo': self.ignorer_geo,
        })

        d_recherche = d_avant_recherche
        u"""
        Parcours tous les jours inclus entre la date de début de recherche et la date de fin de recherche.
        Prends en compte les équipes qui peuvent effectuer la tache, et qui sont disponibles
        Ne prends pas en compte les jours non travaillés @TODO: passer les jours travaillés en many2many vers of.jour (module of_utils)
        """
        while d_recherche < d_apres_recherche:
            d_recherche += un_jour
            num_jour = d_recherche.isoweekday()

            # Restriction aux jours spécifiés dans le service
            while num_jour not in jours:
                d_recherche += un_jour
                num_jour = (num_jour + 1) % 7
            # Arreter la recherche si on dépasse la date de fin
            if d_recherche >= d_apres_recherche:
                continue
            str_d_recherche = fields.Date.to_string(d_recherche)

            # Recherche de creneaux pour la date voulue et les équipes sélectionnées
            dt_jour_deb = tz.localize(datetime.strptime(str_d_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
            dt_jour_fin = tz.localize(datetime.strptime(str_d_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
            # Récupération des évenements déjà planifiées
            events = calendar_obj.search([
                                        ('start_datetime', '<=', str_d_recherche),
                                        ('stop_datetime', '>=', str_d_recherche),
                                        #('start_date', '=', str_d_recherche)
                                        ], order='start_date')
            for event in events:
                if self.user_id.partner_id.id not in event.partner_ids._ids:
                    events -= event

            event_dates_all = []
            for event in events:
                event_dates = [event]
                for event_date in (event.start_datetime, event.stop_datetime):
                    # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                    dt_event_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(event_date))

                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    dt_event_local = max(dt_event_local, dt_jour_deb)
                    dt_event_local = min(dt_event_local, dt_jour_fin)
                    flo_dt_event_local = round(dt_event_local.hour +
                                           dt_event_local.minute / 60.0 +
                                           dt_event_local.second / 3600.0, 5)
                    event_dates.append(flo_dt_event_local)
                event_dates_all.append(event_dates)

            deb = self.hor_md
            fin = self.hor_mf
            ad = self.hor_ad
            creneaux = []
            #TODO: possibilité intervention chevauchant la nuit
            for event, event_deb, event_fin in event_dates_all + [(False, 24, 24)]:
                if deb < event_deb and deb < fin:
                    # Un trou dans le planning, suffisant pour un créneau?
                    if deb < ad and event_deb >= ad:
                        # On passe du matin à l'après-midi
                        # On vérifie la durée cumulée de la matinée et de l'après-midi car une intervention peut
                        # commencer avant la pause repas
                        event_deb = min(event_deb, self.hor_af)
                        duree = self.hor_mf - deb + event_deb - ad
                        if duree >= self.duree:
                            creneaux.append((deb, fin))
                            creneaux.append((ad, event_deb))
                        fin = self.hor_af
                    else:
                        duree = min(event_deb, fin) - deb
                        if duree >= self.duree:
                            creneaux.append((deb, deb+duree))

                if event_fin >= fin and fin <= ad:
                    deb = max(event_fin, ad)
                    fin = self.hor_af
                elif event_fin > deb:
                    deb = event_fin
            if not creneaux:
                # Aucun creneau libre pour cette équipe
                continue
            # création des créneaux dispos
            for event_deb, event_fin, in creneaux:
                description = "%s-%s" % tuple(hours_to_strs(event_deb, event_fin))

                dt_debut = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=event_deb)
                dt_debut = tz.localize(dt_debut, is_dst=None).astimezone(pytz.utc)
                dt_fin = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=event_fin)
                dt_fin = tz.localize(dt_fin, is_dst=None).astimezone(pytz.utc)

                wizard_line_obj.create({
                    'debut_dt': dt_debut,
                    'fin_dt': dt_fin,
                    'date_flo': event_deb,
                    'date_flo_deadline': event_fin,
                    'date': str_d_recherche,
                    'description': description,
                    'wizard_id': self.id,
                    #'user_id': self.user_id.id,
                    'user_partner_id': self.user_id.partner_id.id,
                    'calendar_id': False,
                    'ignorer_geo': self.ignorer_geo,
                })
            # création des créneaux de rdvs
            for event, event_deb, event_fin in event_dates_all:
                description = "%s-%s" % tuple(hours_to_strs(event_deb, event_fin))

                dt_debut = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=event_deb)
                dt_debut = tz.localize(dt_debut, is_dst=None).astimezone(pytz.utc)
                dt_fin = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=event_fin)
                dt_fin = tz.localize(dt_fin, is_dst=None).astimezone(pytz.utc)

                wizard_line_obj.create({
                    'debut_dt': dt_debut, # datetime utc
                    'fin_dt': dt_fin, # datetime utc
                    'date_flo': event_deb,
                    'date_flo_deadline': event_fin,
                    'date': str_d_recherche,
                    'description': description,
                    'wizard_id': self.id,
                    #'user_id': event.user_id.id,
                    'user_partner_id': event.user_id.partner_id.id,
                    'calendar_id': event.id,
                    'partner_ids': event.partner_ids._ids,
                    'name': event.name,
                    'disponible': False,
                    'ignorer_geo': self.ignorer_geo,
                })
        # Calcul des durées et distances
        d_debut = d_avant_recherche + un_jour
        d_fin = d_apres_recherche - un_jour
        if not self.ignorer_geo:
            wizard_line_obj.calc_distances_dates(d_debut, d_fin)

        nb, nb_dispo, first_res = wizard_line_obj.get_nb_dispo(self)

        vals ={}
        # Sélection du résultat
        if nb > 0:
            address = self.rdv_address_id
            name = address.name or (address.parent_id and address.parent_id.name) or ''
            name += address.zip and (" " + address.zip) or ""
            name += address.city and (" " + address.city) or ""

            d_first_res = fields.Date.from_string(first_res.date)
            dt_propos = datetime.combine(d_first_res, datetime.min.time()) + timedelta(hours=first_res.date_flo) # datetime naive
            dt_propos = tz.localize(dt_propos, is_dst=None).astimezone(pytz.utc) # datetime utc

            vals = {
                'date_display'    : first_res.date,
                'name'            : name,
                'user_id'       : first_res.user_id.id,
                'date_propos'     : dt_propos, # datetime utc
                'date_propos_hour': first_res.date_flo,
                'res_line_id'     : first_res.id,
                'display_search'  : False,
                'display_res'     : True,
                'zero_result'     : False,
                'zero_dispo'      : False,
            }

            if nb_dispo == 0:
                vals['display_search'] = True
                vals['display_res'] = False
                vals['zero_dispo'] = True

        else:
            vals = {
                'display_search': True,
                'display_res' : False,
                'zero_result': True,
                'zero_dispo': False,
            }

        self.write(vals)
        if self.res_line_id:
            self.res_line_id.selected = True

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        calendar_obj = self.env['calendar.event']

        # verifier que la date de début et la date de fin sont dans les créneaux
        td_pause_midi = timedelta(hours=self.hor_ad - self.hor_mf)
        td_pause_nuit = timedelta(hours=24 - self.hor_af + self.hor_md)
        dt_propos = fields.Datetime.from_string(self.date_propos) # datetime utc proposition de rdv
        dt_propos_deadline = dt_propos + timedelta(hours=self.duree) # datetime utc proposition fin de rdv
        propos_deadline_flo = self.date_propos_hour + self.duree
        found = False
        err = False
        for planning in self.creneau_ids.search([],order="debut_dt"):
            debut_dt = fields.Datetime.from_string(planning.debut_dt)
            fin_dt = fields.Datetime.from_string(planning.fin_dt)
            if err:
                continue
            elif debut_dt <= dt_propos and fin_dt >= dt_propos and not planning.calendar_id: # le debut du rdv est dans un créneau dispo
                found = True
                if debut_dt <= dt_propos_deadline and fin_dt >= dt_propos_deadline: # le rdv se termine dans ce même créneau
                    break
                elif self.date_propos_hour <= self.hor_mf and dt_propos_deadline > fin_dt: # chevauchement pause midi
                    dt_propos_deadline += td_pause_midi
                    propos_deadline_flo += self.hor_ad - self.hor_mf
                elif self.date_propos_hour <= self.hor_af and dt_propos_deadline > fin_dt: # chevauchement nuit
                    dt_propos_deadline += td_pause_nuit
                    propos_deadline_flo = (propos_deadline_flo + 24 - self.hor_af + self.hor_md) % 24
            elif found and planning.calendar_id: # une intervention entre le début et la fin du rdv
                err = True
            elif found and debut_dt <= dt_propos_deadline and fin_dt >= dt_propos_deadline and not planning.calendar_id: # la fin du rdv est dans un créneau dispo
                break
        else:
            raise UserError(u"Vérifier la date de RDV et l'équipe technique")

        if (not self.hor_md) or (not self.hor_mf) or (not self.hor_ad) or (not self.hor_af):
            raise UserError("Il faut configurer l'horaire de travail de toutes les équipes.")

        """partner_attendees = self.env['res.partner']
        partner_attendees |= self.partner_id
        partner_attendees |= self.user_id.partner_id"""

        values = {
            'name': self.name,
            'state': 'open',
            'start': fields.Datetime.to_string(dt_propos),
            'stop': fields.Datetime.to_string(dt_propos_deadline),
            'user_id': self.user_id.id,
            'allday': self.allday,
            'description': self.description or '',
            'partner_ids': [(4,self.user_id.partner_id.id,False),(4,self.partner_id.id,False)],
            #'partner_ids': partner_attendees,
        }

        calendar_obj.create(values)

        return {'type': 'ir.actions.act_window_close'}


class OfRDVCommercialLine(models.TransientModel):
    _name = 'of.rdv.commercial.line'
    _description = 'Propositions des RDVs'
    _order = "date, date_flo"
    _inherit = "of.calendar.mixin"

    @api.model
    def calc_distances_dates(self,date_debut,date_fin):
        u"""
            une requete http par jour par équipe. En cas de problemes de performances on pourra se débrouiller pour faire une requête par équipe 
        @TODO: revoir cette fonction, origine
        """
        un_jour = timedelta(days=1)
        date_courante = date_debut
        while date_courante <= date_fin:
            creneaux = self.search([('date', '=', date_courante)],order="debut_dt")
            interventions = creneaux.mapped("calendar_id")
            #tournee = interventions.mapped("tournee_id")
            if len(creneaux) == 0:
                continue
            """if len(tournee) == 1: # si tournee on favorise le point de départ de la tournee plutot que celui de l'équipe
                origine = tournee.address_depart_id or creneaux[0].user_id.address_id
                arrivee = tournee.address_retour_id or creneaux[0].user_id.address_retour_id or creneaux[0].user_id.address_id
            else:
                origine = creneaux[0].user_id.address_id or creneaux[0].user_id.employee_ids[0].address_id
                arrivee = creneaux[0].user_id.address_retour_id or creneaux[0].user_id.address_id or creneaux[0].user_id.employee_ids[0].address_id"""
            str_coords = u""
            coords = []
            #TODO: utiliser le serveur OSRM OpenFire
            query = u"https://router.project-osrm.org/route/v1/driving/"
            ### listess de coordonnées: ATTENTION OSRM prend ses coordonnées sous forme (lng,lat)
            # point de départ
            if origine.geo_lat != 0 or origine.geo_lng != 0:
                str_coords += str(origine.geo_lng) + "," + str(origine.geo_lat)
                coords.append((origine.geo_lng,origine.geo_lat))
            else:
                raise UserError("l'origine n'est pas géolocalisée")
            # créneaux et interventions
            for line in creneaux:
                if line.geo_lat != 0 or line.geo_lng != 0:
                    str_coords += u";" + str(line.geo_lng) + u"," + str(line.geo_lat)
                    coords.append((line.geo_lng,line.geo_lat))
            # point d'arrivée
            if arrivee.geo_lat != 0 or arrivee.geo_lng != 0:
                str_coords += u";" + str(arrivee.geo_lng) + "," + str(arrivee.geo_lat)
                coords.append((arrivee.geo_lng,arrivee.geo_lat))
            else:
                raise UserError("le point de retour n'est pas géolocalisé")
            query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
            full_query = query_send + str_coords + "?"
            try:
                req = requests.get(full_query)
                res = req.json()
            except Exception as e:
                raise UserError((u"Impossible de contacter le serveur de routing. Assurez-vous que votre connexion Internet est opérationnelle et que l'URL est définie (%s)") % e)

            if res and res.get(u"routes",False):
                legs = res[u"routes"][0][u"legs"]
                if len(creneaux) == len(res[u"routes"][0][u"legs"]) - 1: # depart -> creneau -> arrivee : 2 routes 1 creneau
                    mode_recherche = creneaux[0].wizard_id.mode_recherche
                    maxi = creneaux[0].wizard_id.max_recherche
                    for i in range(len(creneaux)):
                        vals = {}
                        if i >= 1 and not (creneaux[i-1].calendar_id or creneaux[i].calendar_id):
                            # les creneaux précedant et actuel sont disponible, considérer qu'ils sont le même en terme de distances
                            vals[u"dist_prec"] = legs[i-1][u"distance"] / 1000
                            vals[u"duree_prec"] = legs[i-1][u"duration"] / 60
                            if i < len(creneaux) - 1:
                                vals[u"dist_suiv"] = legs[i+1][u"distance"] / 1000
                                vals[u"duree_suiv"] = legs[i+1][u"duration"] / 60
                            vals[u"distance"] = vals[u"dist_prec"] + vals.get(u"dist_suiv",0)
                            vals[u"duree"] = vals[u"duree_prec"] + vals.get(u"duree_suiv",0)
                            vals_prec = {}
                            vals_prec[u"dist_suiv"] = vals.get(u"dist_suiv",0)
                            vals_prec[u"duree_suiv"] = vals.get(u"duree_suiv",0)
                            vals_prec[u"distance"] = creneaux[i-1].dist_prec + vals_prec[u"dist_suiv"]
                            vals_prec[u"duree"] = creneaux[i-1].duree_prec + vals_prec[u"duree_suiv"]
                            # créneau plus loins que la recherche accepte
                            if creneaux[i-1].disponible and mode_recherche == u"distance" and vals_prec[u"distance"] > maxi:
                                vals_prec[u"force_color"] = "#FF0000"
                                vals_prec[u"name"] = "TROP LOINS"
                                vals_prec[u"disponible"] = False
                            # créneau plus loins que la recherche accepte
                            elif creneaux[i-1].disponible and mode_recherche == u"duree" and vals_prec[u"duree"] > maxi:
                                vals_prec[u"force_color"] = "#FF0000"
                                vals_prec[u"name"] = "TROP LOINS"
                                vals_prec[u"disponible"] = False
                            # trajet aller-retour plus long que la durée de l'intervention
                            elif creneaux[i-1].disponible and vals[u"duree"] > creneaux[i].wizard_id.duree:
                                vals[u"force_color"] = "#AA0000"
                                vals[u"name"] = "TROP COURT"
                                vals[u"disponible"] = False
                            creneaux[i-1].update(vals_prec)
                        else:
                            vals[u"dist_prec"] = legs[i][u"distance"] / 1000
                            vals[u"duree_prec"] = legs[i][u"duration"] / 60
                            vals[u"dist_suiv"] = legs[i+1][u"distance"] / 1000 # legs[i+1] ok car len(legs) == len(creneaux) + 1
                            vals[u"duree_suiv"] = legs[i+1][u"duration"] / 60
                            vals[u"distance"] = vals[u"dist_prec"] + vals.get(u"dist_suiv",0)
                            vals[u"duree"] = vals[u"duree_prec"] + vals.get(u"duree_suiv",0)
                        # créneau plus loins que la recherche accepte
                        if creneaux[i].disponible and mode_recherche == u"distance" and vals[u"distance"] > maxi:
                            vals[u"force_color"] = "#FF0000"
                            vals[u"name"] = "TROP LOINS"
                            vals[u"disponible"] = False
                        # créneau plus loins que la recherche accepte
                        elif creneaux[i].disponible and mode_recherche == u"duree" and vals[u"duree"] > maxi:
                            vals[u"force_color"] = "#FF0000"
                            vals[u"name"] = "TROP LOINS"
                            vals[u"disponible"] = False
                        # trajet aller-retour plus long que la durée de l'intervention
                        elif creneaux[i].disponible and vals[u"duree"] > creneaux[i].wizard_id.duree:
                            vals[u"force_color"] = "#AA0000"
                            vals[u"name"] = "TROP COURT"
                            vals[u"disponible"] = False

                        creneaux[i].update(vals)
            else:
                raise UserWarning("Erreur inattendue de routing")
            date_courante += un_jour

    @api.model
    def get_nb_dispo(self,wizard):
        """Retourne le nombre de créneaux disponibles (qui correspondent aux criteres de recherche), 
            le nomre de créneau trop loins, et le premier resultat (en fonction du critere de résultat"""
        if wizard.mode_result == "distance":
            le_order = "distance,debut_dt"
        else:
            le_order = "debut_dt,distance"
        # ne pas inclure les lignes associées a une event ni les lignes de début et fin de recherche
        lines = self.search([('wizard_id', '=', wizard.id),('virtuel', '=', False),('calendar_id', '=', False)],order=le_order) # events allDay sont debut et fin de recherche
        lines_dispo = self.search([('wizard_id', '=', wizard.id),('disponible', '=', True)],order=le_order)
        nb = len(lines)
        nb_dispo = len(lines_dispo)
        first_res = lines_dispo and lines_dispo[0] or lines and lines[0] or False
        return (nb,nb_dispo,first_res)

    date = fields.Date(string="Date")
    debut_dt = fields.Datetime(string="Début")
    fin_dt = fields.Datetime(string="Fin")
    date_flo = fields.Float(string='Date', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    description = fields.Char(string='RDV', size=128)
    wizard_id = fields.Many2one('of.rdv.commercial', string="RDV", required=True, ondelete='cascade')
    user_id = fields.Many2one(related="wizard_id.user_id")
    user_partner_id = fields.Many2one('res.partner',string="user partner")
    partner_ids = fields.Many2many('res.partner', 'calendar_event_res_rdvcom_rel', string='Attendees')
    calendar_id = fields.Many2one('calendar.event', string="Planning")
    name = fields.Char(string="name", default="DISPONIBLE")
    distance = fields.Float(string='Dist.tot. (km)',help="distance prec + distance suiv")
    dist_prec = fields.Float(string='Dist.Prec. (km)')
    dist_suiv = fields.Float(string='Dist.Suiv. (km)')
    duree = fields.Float(string=u'Durée.tot. (min)',help="durée prec + durée suiv")
    duree_prec = fields.Float(string=u'Durée.Prec. (min)')
    duree_suiv = fields.Float(string=u'Durée.Suiv. (min)')
    of_color_ft = fields.Char(related="user_id.of_color_ft", readonly=True)
    of_color_bg = fields.Char(related="user_id.of_color_bg", readonly=True)
    disponible = fields.Boolean(string="Est dispo", default=True)
    force_color = fields.Char("Couleur")
    allday = fields.Boolean('All Day', default=False)
    virtuel = fields.Boolean('Virtuel', default=False)
    selected = fields.Boolean(u'Créneau sélectionné', default=False)

    ignorer_geo = fields.Boolean(u"Ignorer données géographiques")
    geo_lat = fields.Float(string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", compute="_compute_geo", readonly=True)
    geo_lng = fields.Float(string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", compute="_compute_geo", readonly=True)
    precision = fields.Selection([
        ('manual', "Manuel"),
        ('high', "Haut"),
        ('medium', "Moyen"),
        ('low', "Bas"),
        ('no_address', u"--"),
        ('unknown', u"Indéterminé"),
        ('not_tried', u"Pas tenté"),
        ], default='not_tried', readonly=True, help=u"Niveau de précision de la géolocalisation", compute="_compute_geo")

    @api.multi
    @api.depends("calendar_id")
    def _compute_geo(self):
        for line in self:
            if line.calendar_id: # correspond a un creneau d'intervention
                vals = {
                    'geo_lat': line.calendar_id.geo_lat,
                    'geo_lng': line.calendar_id.geo_lng,
                    'precision': line.calendar_id.precision,
                }
            else: # correspond a un creneau libre
                vals = {
                    'geo_lat': line.wizard_id.geo_lat,
                    'geo_lng': line.wizard_id.geo_lng,
                    'precision': line.wizard_id.precision,
                }
            line.update(vals)

    @api.depends('calendar_id')
    def _compute_state_int(self):
        """de of.calendar.mixin"""
        for line in self:
            interv = line.calendar_id
            if interv:
                if interv.state and interv.state == "draft":
                    line.state_int = 0
                elif interv.state and interv.state == "open":
                    line.state_int = 1
                elif interv.state and interv.state == "done":
                    line.state_int = 2
            else:
                line.state_int = 3

    @api.model
    def get_state_int_map(self):
        """de of.calendar.mixin"""
        v0 = {'label': 'Brouillon', 'value': 0}
        v1 = {'label': u'Confirmé', 'value': 1}
        v2 = {'label': u'Réalisé', 'value': 2}
        v3 = {'label': u'Disponibilité', 'value': 3}
        return (v0, v1, v2, v3)

    @api.multi
    def button_select(self):
        """Sélectionne ce créneau en temps que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        rdv_line_obj = self.env["of.rdv.commercial.line"]
        selected_line = rdv_line_obj.search([("selected","=",True)])
        selected_line.selected = False
        self.selected = True

        address = self.wizard_id.rdv_address_id
        name = address.name or (address.parent_id and address.parent_id.name) or ''
        name += address.zip and (" " + address.zip) or ""
        name += address.city and (" " + address.city) or ""
        wizard_vals = {
            'date_display'    : self.date,#.strftime('%A %d %B %Y'),
            'name'            : name,
            'date_propos'     : self.debut_dt,
            'date_propos_hour': self.date_flo,
            'res_line_id'     : self.id,
        }
        self.wizard_id.write(wizard_vals)

        return {'type': 'ir.actions.do_nothing'}
