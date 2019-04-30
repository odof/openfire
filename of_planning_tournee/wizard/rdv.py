# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date as d_date
import pytz
from odoo.exceptions import UserError

import urllib

try:
    import requests
except ImportError:
    requests = None

SEARCH_MODES = [
    ('distance', u'Distance (km)'),
    ('duree', u'Durée (min)'),
]

ROUTING_BASE_URL = "http://s-hotel.openfire.fr:5000/"
ROUTING_VERSION = "v1"
ROUTING_PROFILE = "driving"

def hours_to_strs(*hours):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return tuple("%02dh%02d" % (hour, round((hour % 1) * 60)) for hour in hours)

class OfTourneeRdv(models.TransientModel):
    _name = 'of.tournee.rdv'
    _description = u'Prise de RDV dans les tournées'

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

    name = fields.Char(string=u'Libellé', size=64, required=False)
    description = fields.Html(string='Description')
    tache_id = fields.Many2one('of.planning.tache', string='Prestation', required=True)
    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe")
    pre_equipe_ids = fields.Many2many('of.planning.equipe', string=u'Équipes', domain="[('tache_ids', 'in', tache_id)]")
    duree = fields.Float(string=u'Durée', required=True, digits=(12, 5))
    planning_ids = fields.One2many('of.tournee.rdv.line', 'wizard_id', string='Proposition de RDVs')
    date_propos = fields.Datetime(string=u'RDV Début')
    date_propos_hour = fields.Float(string=u'Heude de début', digits=(12, 5))
    date_recherche_debut = fields.Date(string='À partir du', required=True, default=lambda *a: (d_date.today() + timedelta(days=1)).strftime('%Y-%m-%d'))
    date_recherche_fin = fields.Date(string="Jusqu'au", required=True, default=lambda *a: (d_date.today() + timedelta(days=7)).strftime('%Y-%m-%d'))
    partner_id = fields.Many2one('res.partner', string='Client', required=True, readonly=True, default=_default_partner)
    partner_address_id = fields.Many2one(
        'res.partner', string="Adresse d'intervention", required=True, default=_default_address,
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    partner_address_street = fields.Char(related="partner_address_id.street", readonly=True)
    partner_address_street2 = fields.Char(related="partner_address_id.street2", readonly=True)
    partner_address_city = fields.Char(related="partner_address_id.city", readonly=True)
    partner_address_state_id = fields.Many2one(related="partner_address_id.state_id", readonly=True)
    partner_address_zip = fields.Char(related="partner_address_id.zip", readonly=True)
    partner_address_country_id = fields.Many2one(related="partner_address_id.country_id", readonly=True)
    date_display = fields.Char(string='Jour du RDV', size=64, readonly=True)
    service_id = fields.Many2one(
        'of.service', string='Service client', default=_default_service,
        domain="[('partner_id', '=', partner_id)]")
    creer_recurrence = fields.Boolean(
        string="Créer récurrence?", default=True,
        help="Si cette case est cochée et qu'il n'existe pas de service lié à cette intervention, en crééra un.")
    date_next = fields.Date(string=u'Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention")
    mode_recherche = fields.Selection(SEARCH_MODES, string="Mode de recherche", required=True, default="distance")
    max_recherche = fields.Float(string="Maximum")

    zero_result = fields.Boolean(string="Recherche infructueuse", default=False, help="Aucun résultat")
    zero_dispo = fields.Boolean(string="Recherche infructueuse", default=False, help="Aucun résultat suffisamment proche")
    display_res = fields.Boolean(string=u"Voir Résultats", default=False)
    res_line_id = fields.Many2one("of.tournee.rdv.line", string="Créneau Sélectionné")

    # champs ajoutés pour la vue map
    geo_lat = fields.Float(related='partner_address_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='partner_address_id.geo_lng', readonly=True)
    precision = fields.Selection(related='partner_address_id.precision', readonly=True)
    partner_name = fields.Char(related='partner_id.name')
    geocode_retry = fields.Boolean("Geocodage retenté")
    ignorer_geo = fields.Boolean("Ignorer données géographiques")

    @api.onchange('mode_recherche')
    def _onchange_mode_recherche(self):
        self.ensure_one()
        if self.mode_recherche:
            self.max_recherche = self.mode_recherche == 'distance' and 50 or 60

    @api.onchange('date_recherche_debut')
    def _onchange_date_recherche_debut(self):
        self.ensure_one()
        if self.date_recherche_debut:
            date_deb = fields.Date.from_string(self.date_recherche_debut)
            date_fin = date_deb + timedelta(days=6)
            self.date_recherche_fin = fields.Date.to_string(date_fin)

    @api.onchange('date_recherche_fin')
    def _onchange_date_recherche_fin(self):
        self.ensure_one()
        if self.date_recherche_fin and self.date_recherche_fin < self.date_recherche_debut:
            raise UserError(u"La date de fin de recherche doit être postérieure à la date de début de recherche")

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        service_obj = self.env['of.service']
        service = False
        vals = {'service_id': False}
        if self.tache_id:
            if self.service_id and self.service_id.tache_id.id == self.tache_id.id:
                del vals['service_id']
            else:
                service = service_obj.search([('partner_id', '=', self.partner_id.id),
                                              ('tache_id', '=', self.tache_id.id)], limit=1)
                if service:
                    vals['service_id'] = service

            if self.tache_id.duree:
                vals['duree'] = self.tache_id.duree

            equipes = []
            for equipe in self.pre_equipe_ids:
                if equipe in self.tache_id.equipe_ids:
                    equipes.append(equipe.id)
            vals['pre_equipe_ids'] = equipes
        self.update(vals)

    @api.onchange('service_id')
    def _onchange_service(self):
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

    @api.multi
    def _get_equipe_possible(self):
        self.ensure_one()
        equipe_ids = []
        for planning in self.planning_ids:
            if planning.equipe_id.id not in equipe_ids:
                equipe_ids.append(planning.equipe_id.id)
        return equipe_ids

    @api.multi
    def button_geocode(self):
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
        Calcule la prochaine intervention à partir du lendemain de la date courante
        @todo: Remplacer le retour d'action par un return True, mais pour l'instant cela
          ne charge pas correctement la vue du planning.
        """
        self.compute()
        context = dict(self._context, equipe_domain=self._get_equipe_possible())
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
    def compute(self):
        u"""Calcul des prochains créneaux disponibles
        NOTE : Si un service est sélectionné incluant le samedi et/ou le dimanche,
               ceux-cis seront traités comme des jours normaux du point de vue des équipes
        """
        self.ensure_one()

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        equipe_obj = self.env['of.planning.equipe']
        wizard_line_obj = self.env['of.tournee.rdv.line']
        intervention_obj = self.env['of.planning.intervention']

        address = self.partner_address_id
        service = self.service_id
        jours = [jour.numero for jour in service.jour_ids] if service else range(1, 6)

        # Suppression des anciens créneaux
        self.planning_ids.unlink()

        # Récupération des équipes
        equipes = self.env['of.planning.equipe']
        if not self.tache_id.equipe_ids:
            raise UserError(u"Aucune équipe ne peut réaliser cette tâche.")
        if self.pre_equipe_ids:
            for equipe in self.pre_equipe_ids:
                if equipe in self.tache_id.equipe_ids:
                    equipes |= equipe
            if len(equipes) == 0:
                raise UserError(u"Aucune des équipes sélectionnées n'a la compétence pour réaliser cette prestation.")
        else:
            equipes = self.tache_id.equipe_ids

        un_jour = timedelta(days=1)

        # --- Création des créneaux de début et fin de recherche ---
        d_avant_recherche = fields.Date.from_string(self.date_recherche_debut) - un_jour
        avant_recherche = fields.Date.to_string(d_avant_recherche)
        dt_avant_recherche_debut = tz.localize(datetime.strptime(avant_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        dt_avant_recherche_fin = tz.localize(datetime.strptime(avant_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        d_apres_recherche = fields.Date.from_string(self.date_recherche_fin) + un_jour
        apres_recherche = fields.Date.to_string(d_apres_recherche)
        dt_apres_recherche_debut = tz.localize(datetime.strptime(apres_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        dt_apres_recherche_fin = tz.localize(datetime.strptime(apres_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime

        for equipe in equipes:
            wizard_line_obj.create({
                'name': u"Début de la recherche",
                'debut_dt': dt_avant_recherche_debut,
                'fin_dt': dt_avant_recherche_fin,
                'date_flo': 0.0,
                'date_flo_deadline': 23.9,
                'date': d_avant_recherche,
                'wizard_id': self.id,
                'equipe_id': equipe.id,
                'intervention_id': False,
                'disponible': False,
                'allday': True,
            })
            wizard_line_obj.create({
                'name': "Fin de la recherche",
                'debut_dt': dt_apres_recherche_debut,
                'fin_dt': dt_apres_recherche_fin,
                'date_flo': 0.0,
                'date_flo_deadline': 23.9,
                'date': d_apres_recherche,
                'wizard_id': self.id,
                'equipe_id': equipe.id,
                'intervention_id': False,
                'disponible': False,
                'allday': True,
            })

        # --- Recherche des créneaux ---
        d_recherche = d_avant_recherche
        u"""
        Parcourt tous les jours inclus entre la date de début de recherche et la date de fin de recherche.
        Prend en compte les équipes qui peuvent effectuer la tache, et qui sont disponibles
        Ne prend pas en compte les jours non travaillés
        @TODO: passer les jours travaillés en many2many vers of.jour (module of_utils)
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

            # Interdiction de chercher dans les tournées bloquées ou complètes
            self._cr.execute("SELECT equipe_id "
                             "FROM of_planning_tournee "
                             "WHERE equipe_id IN %s "
                             "  AND date = %s"
                             "  AND (is_bloque OR is_complet)",
                             (equipe._ids, str_d_recherche))
            equipes_bloquees = [row[0] for row in self._cr.fetchall()]
            equipes_dispo = [equipe_id for equipe_id in equipes._ids if equipe_id not in equipes_bloquees]
            if not equipes_dispo:
                continue

            # Recherche de créneaux pour la date voulue et les équipes sélectionnées
            dt_jour_deb = tz.localize(datetime.strptime(str_d_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
            dt_jour_fin = tz.localize(datetime.strptime(str_d_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
            # Récupération des interventions déjà planifiées
            interventions = intervention_obj.search([('equipe_id', 'in', equipes_dispo),
                                                     ('date', '<=', str_d_recherche),
                                                     ('date_deadline', '>=', str_d_recherche),
                                                     ('state', 'in', ('draft', 'confirm')),
                                                     ], order='date')

            equipe_intervention_dates = {equipe_id: [] for equipe_id in equipes_dispo}
            for intervention in interventions:
                intervention_dates = [intervention]
                for intervention_date in (intervention.date, intervention.date_deadline):
                    # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                    dt_intervention_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention_date))

                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    dt_intervention_local = max(dt_intervention_local, dt_jour_deb)
                    dt_intervention_local = min(dt_intervention_local, dt_jour_fin)
                    flo_dt_intervention_local = round(dt_intervention_local.hour +
                                                      dt_intervention_local.minute / 60.0 +
                                                      dt_intervention_local.second / 3600.0, 5)
                    intervention_dates.append(flo_dt_intervention_local)

                equipe_intervention_dates[intervention.equipe_id.id].append(intervention_dates)

            # Calcul des créneaux
            # @todo: Gestion des employés dans plusieurs équipes
            for equipe in equipe_obj.browse(equipes_dispo):
                intervention_dates = equipe_intervention_dates[equipe.id]
                deb = equipe.hor_md
                fin = equipe.hor_mf
                ad = equipe.hor_ad
                creneaux = []
                # @todo: Possibilité intervention chevauchant la nuit
                for intervention, intervention_deb, intervention_fin in intervention_dates + [(False, 24, 24)]:
                    if deb < intervention_deb and deb < fin:
                        # Un trou dans le planning, suffisant pour un créneau?
                        if deb < ad and intervention_deb >= ad:
                            # On passe du matin à l'après-midi
                            # On vérifie la durée cumulée de la matinée et de l'après-midi car une intervention peut
                            # commencer avant la pause repas
                            intervention_deb = min(intervention_deb, equipe.hor_af)
                            duree = equipe.hor_mf - deb + intervention_deb - ad
                            if duree >= self.duree:
                                # deb < fin donc il y a du temps disponible le matin
                                creneaux.append((deb, fin, equipe))
                                if ad < intervention_deb:
                                    # Il y a du temps disponible entre le début d'après-midi et le début de l'intervention
                                    creneaux.append((ad, intervention_deb, equipe))
                            fin = equipe.hor_af
                        else:
                            duree = min(intervention_deb, fin) - deb
                            if duree >= self.duree:
                                creneaux.append((deb, deb+duree, equipe))

                    if intervention_fin >= fin and fin <= ad:
                        deb = max(intervention_fin, ad)
                        fin = equipe.hor_af
                    elif intervention_fin > deb:
                        deb = intervention_fin
                if not creneaux:
                    # Aucun creneau libre pour cette équipe
                    continue

                # Création des créneaux disponibles
                for intervention_deb, intervention_fin, equipe in creneaux:
                    description = "%s-%s" % tuple(hours_to_strs(intervention_deb, intervention_fin))

                    dt_debut = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=intervention_deb)
                    dt_debut = tz.localize(dt_debut, is_dst=None).astimezone(pytz.utc)
                    dt_fin = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=intervention_fin)
                    dt_fin = tz.localize(dt_fin, is_dst=None).astimezone(pytz.utc)

                    wizard_line_obj.create({
                        'debut_dt': dt_debut,
                        'fin_dt': dt_fin,
                        'date_flo': intervention_deb,
                        'date_flo_deadline': intervention_fin,
                        'date': str_d_recherche,
                        'description': description,
                        'wizard_id': self.id,
                        'equipe_id': equipe.id,
                        'intervention_id': False,
                    })
                # Création des créneaux d'intervention
                for intervention, intervention_deb, intervention_fin in intervention_dates:
                    description = "%s-%s" % tuple(hours_to_strs(intervention_deb, intervention_fin))

                    dt_debut = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=intervention_deb)
                    dt_debut = tz.localize(dt_debut, is_dst=None).astimezone(pytz.utc)
                    dt_fin = datetime.combine(d_recherche, datetime.min.time()) + timedelta(hours=intervention_fin)
                    dt_fin = tz.localize(dt_fin, is_dst=None).astimezone(pytz.utc)

                    wizard_line_obj.create({
                        'debut_dt': dt_debut,  # datetime utc
                        'fin_dt': dt_fin,  # datetime utc
                        'date_flo': intervention_deb,
                        'date_flo_deadline': intervention_fin,
                        'date': str_d_recherche,
                        'description': description,
                        'wizard_id': self.id,
                        'equipe_id': intervention.equipe_id.id,
                        'intervention_id': intervention.id,
                        'name': intervention.name,
                        'disponible': False,
                    })
        # Calcul des durées et distances
        d_debut = d_avant_recherche + un_jour
        d_fin = d_apres_recherche - un_jour
        if not self.ignorer_geo:
            self.calc_distances_dates_equipes(d_debut, d_fin, equipes)

        nb, nb_dispo, first_res = wizard_line_obj.get_nb_dispo(self)

        vals = {}
        # Sélection du résultat
        if nb > 0:
            address = self.partner_address_id
            name = address.name or (address.parent_id and address.parent_id.name) or ''
            name += address.zip and (" " + address.zip) or ""
            name += address.city and (" " + address.city) or ""

            d_first_res = fields.Date.from_string(first_res.date)
            dt_propos = datetime.combine(d_first_res, datetime.min.time()) + timedelta(hours=first_res.date_flo)  # datetime naive
            dt_propos = tz.localize(dt_propos, is_dst=None).astimezone(pytz.utc)  # datetime utc

            vals = {
                'date_display'    : first_res.date,
                'name'            : name,
                'equipe_id'       : first_res.equipe_id.id,
                'date_propos'     : dt_propos,  # datetime utc
                'date_propos_hour': first_res.date_flo,
                'res_line_id'     : first_res.id,
                'display_res'     : True,
                'zero_result'     : False,
                'zero_dispo'      : False,
            }

            if self.service_id:
                vals['date_next'] = self.service_id.get_next_date(d_first_res.strftime('%Y-%m-%d'))
            else:
                vals['date_next'] = "%s-%02i-01" % (d_first_res.year + 1, d_first_res.month)

            if nb_dispo == 0:
                vals['display_res'] = True
                vals['zero_dispo'] = True

        else:
            vals = {
                'display_res' : True,
                'zero_result': True,
                'zero_dispo': False,
            }

        self.write(vals)
        if self.res_line_id:
            self.res_line_id.selected = True
            self.res_line_id.selected_hour = self.res_line_id.date_flo

    @api.multi
    def _get_service_data(self, mois):
        return {
            'partner_id': self.partner_id.id,
            'address_id': self.partner_address_id.id,
            'tache_id': self.tache_id.id,
            'mois_ids': [(4, mois)],
            'date_next': self.date_next,
            'note': self.description or '',
        }

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        intervention_obj = self.env['of.planning.intervention']
        service_obj = self.env['of.service']

        # Vérifier que la date de début et la date de fin sont dans les créneaux
        equipe = self.equipe_id
        if (not equipe.hor_md) or (not equipe.hor_mf) or (not equipe.hor_ad) or (not equipe.hor_af):
            raise UserError("Il faut configurer l'horaire de travail de toutes les équipes.")

        td_pause_midi = timedelta(hours=equipe.hor_ad - equipe.hor_mf)
        dt_propos = fields.Datetime.from_string(self.date_propos)  # datetime utc proposition de rdv
        dt_propos_deadline = dt_propos + timedelta(hours=self.duree)  # datetime utc proposition fin de rdv

        rdv_ok = False
        for planning in self.planning_ids.filtered(lambda p: p.equipe_id == equipe):
            fin_dt = fields.Datetime.from_string(planning.fin_dt)

            if fin_dt < dt_propos:
                # Créneau avant le début de l'intervention
                continue
            if fin_dt >= dt_propos_deadline:
                # Créneau suffisant pour terminer l'intervention
                rdv_ok = True
                break
            if fin_dt == 'midi':
                dt_propos_deadline += td_pause_midi
            if fin_dt == 'soir':
                raise UserError('Cet outil ne permet pas de planifier une intervention sur plusieurs jours\n'
                                'Veuillez saisir votre rendez-vous directement dans le planning des interventions.')
        if not rdv_ok:
            raise UserError("RDV PAS OK !!!")

        values = {
            'hor_md': equipe.hor_md,
            'hor_mf': equipe.hor_mf,
            'hor_ad': equipe.hor_ad,
            'hor_af': equipe.hor_af,
            'partner_id': self.partner_id.id,
            'address_id': self.partner_address_id.id,
            'tache_id': self.tache_id.id,
            'equipe_id': self.equipe_id.id,
            'date': self.date_propos,
            'duree': self.duree,
            'user_id': self._uid,
            'company_id': self.partner_address_id.company_id and self.partner_address_id.company_id.id,
            'name': self.name,
            'description': self.description or '',
            'state': 'confirm',
            'verif_dispo': True,
        }

        # Si rdv RES pris depuis un SAV, on le lie au SAV
        if self._context.get('active_model') == 'crm.helpdesk':
            values['sav_id'] = self._context.get('active_id', False)

        res = intervention_obj.create(values)

        # Creation/mise à jour du service si creer_recurrence
        if self.date_next:
            if self.service_id:
                self.service_id.write({'date_next': self.date_next})
            elif self.creer_recurrence:
                service_obj.create(self._get_service_data(dt_propos.month))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.planning.intervention',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': res.id,
            'target': 'current',
            'context': self._context
        }

    @api.multi
    def calc_distances_dates_equipes(self, date_debut, date_fin, equipes):
        u"""
            Une requête http par jour et par équipe.
            En cas de problème de performance on pourra se débrouiller pour faire une requête par équipe.
        """
        self.ensure_one()
        wizard_line_obj = self.env['of.tournee.rdv.line']
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        un_jour = timedelta(days=1)
        date_courante = date_debut
        while date_courante <= date_fin:
            mode_recherche = self.mode_recherche
            maxi = self.max_recherche
            for equipe in equipes:
                creneaux = wizard_line_obj.search([('wizard_id', '=', self.id),
                                                   ('date', '=', date_courante),
                                                   ('equipe_id', '=', equipe.id)], order="debut_dt")
                if len(creneaux) == 0:
                    continue
                tournee = creneaux.mapped("intervention_id").mapped("tournee_id")
                # S'il y a une tournée, on favorise son point de départ plutôt que celui de l'équipe.
                # Note : Une tournée est unique par équipe et par date (contrainte SQL) donc len(tournee) <= 1
                origine = (tournee.address_depart_id or
                           equipe.address_id or
                           equipe.employee_ids[0].address_id)
                arrivee = (tournee.address_retour_id or
                           equipe.address_retour_id or
                           equipe.address_id or
                           equipe.employee_ids[0].address_id)
                if origine.geo_lat == origine.geo_lng == 0:
                    raise UserError(u"L'origine n'est pas géolocalisée.\nÉquipe : %s\nDate : %s" %
                                    (equipe.name, date_courante.strftime(lang.date_format)))
                if arrivee.geo_lat == arrivee.geo_lng == 0:
                    raise UserError(u"Le point de retour n'est pas géolocalisé.\nÉquipe : %s\nDate : %s" %
                                    (equipe.name, date_courante.strftime(lang.date_format)))

                query = ROUTING_BASE_URL + "route/" + ROUTING_VERSION + "/" + ROUTING_PROFILE + "/"

                # Listes de coordonnées: ATTENTION OSRM prend ses coordonnées sous form (lng, lat)
                # Point de départ
                str_coords = str(origine.geo_lng) + "," + str(origine.geo_lat)

                # Créneaux et interventions
                non_loc = False
                for line in creneaux:
                    if line.geo_lat == line.geo_lng == 0:
                        non_loc = True
                        break
                    str_coords += ";" + str(line.geo_lng) + "," + str(line.geo_lat)
                if non_loc:
                    continue

                # Point d'arrivée
                str_coords += ";" + str(arrivee.geo_lng) + "," + str(arrivee.geo_lat)

                query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
                full_query = query_send + str_coords + "?"
                try:
                    req = requests.get(full_query)
                    res = req.json()
                except Exception as e:
                    raise UserError(u"Impossible de contacter le serveur de routing. Assurez-vous que votre connexion Internet est opérationnelle et que l'URL est définie (%s)" % e)

                if res and res.get('routes'):
                    legs = res['routes'][0]['legs']
                    if len(creneaux) == len(res['routes'][0]['legs']) - 1:  # depart -> creneau -> arrivee : 2 routes 1 creneau
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

                            if crens[0].disponible:
                                if mode_recherche == 'distance' and vals['distance'] > maxi:
                                    vals['force_color'] = "#FF0000"
                                    vals['name'] = "TROP LOIN"
                                    vals['disponible'] = False
                                # Créneau plus loin que la recherche accepte
                                elif crens[0].disponible and mode_recherche == 'duree' and vals['duree'] > maxi:
                                    vals['force_color'] = "#FF0000"
                                    vals['name'] = "TROP LOIN"
                                    vals['disponible'] = False
                                # Trajet aller-retour plus long que la durée de l'intervention
                                elif crens[0].disponible and vals['duree'] > self.duree * 60:
                                    # note: On vérifie si la durée de transport est inférieure à la durée de la tâche.
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
    _order = "date, equipe_id, date_flo"
    _inherit = "of.calendar.mixin"

    @api.model
    def get_nb_dispo(self, wizard):
        """Retourne le nombre de créneaux disponibles (qui correspondent aux critères de recherche),
            le nombre de créneaux trop éloignés, et le premier résultat (en fonction du critère de résultat)"""
        # ne pas inclure les lignes associées a une intervention ni les lignes de début et fin de recherche
        lines = self.search([('wizard_id', '=', wizard.id),
                             ('allday', '=', False),
                             ('intervention_id', '=', False)],
                            order="distance, debut_dt")  # events allDay sont debut et fin de recherche
        lines_dispo = self.search([('wizard_id', '=', wizard.id), ('disponible', '=', True)], order="distance, debut_dt")
        nb = len(lines)
        nb_dispo = len(lines_dispo)
        first_res = lines_dispo and lines_dispo[0] or lines and lines[0] or False
        return (nb, nb_dispo, first_res)

    date = fields.Date(string="Date")
    debut_dt = fields.Datetime(string=u"Début")
    fin_dt = fields.Datetime(string="Fin")
    date_flo = fields.Float(string='Date', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    description = fields.Char(string=u"Créneau", size=128)
    wizard_id = fields.Many2one('of.tournee.rdv', string="RDV", required=True, ondelete='cascade')
    equipe_id = fields.Many2one('of.planning.equipe', string='Equipe')
    intervention_id = fields.Many2one('of.planning.intervention', string="Planning")
    name = fields.Char(string="name", default="DISPONIBLE")
    distance = fields.Float(string='Dist.tot. (km)', digits=(12, 2), help="distance prec + distance suiv")
    dist_prec = fields.Float(string='Dist.Prec. (km)')
    dist_suiv = fields.Float(string='Dist.Suiv. (km)')
    duree = fields.Float(string=u'Durée.tot. (min)', digits=(12, 2), help=u"durée prec + durée suiv")
    duree_prec = fields.Float(string=u'Durée.Prec. (min)')
    duree_suiv = fields.Float(string=u'Durée.Suiv. (min)')
    color_ft = fields.Char(related="equipe_id.color_ft", readonly=True)
    color_bg = fields.Char(related="equipe_id.color_bg", readonly=True)
    disponible = fields.Boolean(string="Est dispo", default=True)
    force_color = fields.Char("Couleur")
    allday = fields.Boolean('All Day', default=False)
    selected = fields.Boolean(u'Créneau sélectionné', default=False)
    selected_hour = fields.Float(string='Heure du RDV', digits=(2, 2))
    selected_description = fields.Html(string="Description", related="wizard_id.description")

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
                if interv.state and interv.state == "draft":
                    line.state_int = 0
                elif interv.state and interv.state == "confirm":
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
    def button_confirm(self):
        """Sélectionne ce créneau en temps que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        d = fields.Date.from_string(self.date)
        dt_propos = datetime.combine(d, datetime.min.time()) + timedelta(hours=self.selected_hour)  # datetime local
        dt_propos = tz.localize(dt_propos, is_dst=None).astimezone(pytz.utc)  # datetime utc
        self.wizard_id.date_propos = dt_propos
        return self.wizard_id.button_confirm()

    @api.multi
    def button_select(self):
        """Sélectionne ce créneau en temps que résultat. Appelé depuis la vue form du créneau"""
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
            'date_display'    : self.date,  # .strftime('%A %d %B %Y'),
            'name'            : name,
            'equipe_id'       : self.equipe_id.id,
            'date_propos'     : self.debut_dt,
            'date_propos_hour': self.date_flo,
            'res_line_id'     : self.id,
        }
        if self.wizard_id.service_id:
            d_date = fields.Date.from_string(self.date)
            wizard_vals['date_next'] = self.wizard_id.service_id.get_next_date(d_date.strftime('%Y-%m-%d'))
        self.wizard_id.write(wizard_vals)

        return {'type': 'ir.actions.do_nothing'}
