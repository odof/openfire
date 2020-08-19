# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import json
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from odoo.tools import config
from odoo.addons.of_geolocalize.models.of_geo import GEO_PRECISION
from odoo.addons.of_utils.models.of_utils import hours_to_strs, distance_points as voloiseau, arrondi_sup
import urllib
import requests


class OfPlanifCreneau(models.TransientModel):
    _name = 'of.planif.creneau'
    _description = u'Prise de RDV depuis un créneau disponible'

    # Champs

    # Créneau
    employee_id = fields.Many2one('hr.employee', string="Intervenant", readonly=True)
    date_creneau = fields.Date(string=u"Date du créneau", readonly=True)
    num_jour = fields.Integer(string=u"numéro du jour", compute="_compute_num_jour")
    heure_debut_creneau = fields.Float(string=u'Heure de début', digits=(5, 5))
    heure_fin_creneau = fields.Float(string=u'Heure de fin', digits=(5, 5))
    creneaux_reels = fields.Char(string=u"Créneaux réels")
    creneaux_reels_formatted = fields.Char(string=u"Créneaux réels", compute="_compute_creneaux_reels_formatted")
    duree_creneau = fields.Float(string=u"Durée à planifier")
    duree_creneau_readonly = fields.Float(related="duree_creneau", readonly=True)
    creneau_fini = fields.Boolean(string=u"Créneau entièrement planifiée")

    # Lieu précédent
    lieu_prec_depart = fields.Boolean(string=u"lieu de départ de la journée?", compute="_compute_lieu_depart_arrivee")
    lieu_prec_id = fields.Many2one("res.partner", string=u"lieu précédent")
    lieu_prec_readonly_id = fields.Many2one(related="lieu_prec_id", readonly=True)
    lieu_prec_manual_id = fields.Many2one("res.partner", string=u"lieu précédent (manuel)")
    lieu_prec_message = fields.Selection(
        [('lieu_prec_absent',
          u"Ce créneau n'a pas de lieu précédent.\n"
          u"Cela peut arriver si l'intervention précédente n'a pas d'adresse, ou si l'intervenant n'a pas d'adresse"
          u" de départ.\n"
          u"Veuillez choisir un lieu de précédent pour ce créneau afin de faciliter les calculs de distances.\n"
          u"Si vous ne le faites pas, pas de panique! On considérera que le lieu de précédent est le lieu suivant"),
         ('lieu_prec_non_geoloc',
          u"Le lieu précédent de ce créneau n'est pas géolocalisé\n"
          u"Si vous avez déjà tenté de le géocoder, veuillez choisir un lieu précédent géolocalisé afin de faciliter"
          u" les calculs de distances\n"
          u"Si vous ne le faites pas, pas de panique! On considérera que le lieu de précédent est le lieu suivant")],
        compute="_compute_messages")
    street_prec = fields.Char(compute="compute_prec_suiv_vals")
    zip_prec = fields.Char(compute="compute_prec_suiv_vals")
    city_prec = fields.Char(compute="compute_prec_suiv_vals")
    country_prec_id = fields.Many2one('res.country', compute="compute_prec_suiv_vals")
    geo_lat_prec = fields.Float(compute="compute_prec_suiv_vals")
    geo_lng_prec = fields.Float(compute="compute_prec_suiv_vals")
    precision_prec = fields.Selection(GEO_PRECISION, compute="compute_prec_suiv_vals")

    # Lieu suivant
    lieu_suiv_arrivee = fields.Boolean(string=u"lieu d'arrivée de la journée", compute="_compute_lieu_depart_arrivee")
    lieu_suiv_id = fields.Many2one("res.partner", string="lieu suivant")
    lieu_suiv_readonly_id = fields.Many2one(related="lieu_suiv_id", readonly=True)
    lieu_suiv_manual_id = fields.Many2one("res.partner", string=u"lieu suivant (manuel)")
    lieu_suiv_message = fields.Selection(
        [('lieu_suiv_absent',
          u"Ce créneau n'a pas de lieu suivant.\n"
          u"Cela peut arriver si l'intervention suivante n'a pas d'adresse, ou si l'intervenant n'a pas d'adresse de"
          u" retour.\n"
          u"Veuillez choisir un lieu de suivant pour ce créneau Pour faciliter les calculs de distances.\n"
          u"Si vous ne le faites pas, pas de panique! On considérera que le lieu de suivant est le lieu précédent"),
         ('lieu_suiv_non_geoloc',
          u"Le lieu suivant de ce créneau n'est pas géolocalisé\n"
          u"Si vous avez déjà tenté de le géocoder, veuillez choisir un lieu suivant géolocalisé afin de faciliter"
          u" les calculs de distances\n"
          u"Si vous ne le faites pas, pas de panique! On considérera que le lieu suivant est le lieu précédent"),
         ('lieu_prec_suiv_prob',
          u"Ce créneau n'a ni lieu précédent ni lieu suivant, ou il y a des problèmes de géolocalisation.\n"
          u"Veuillez choisir un lieu précédent et/ou suivant géolocalisés pour ce créneau afin de faciliter les calculs"
          u" de distances.\n"
          u"Si vous ne le faites pas, les résultat proposés ne tiendront pas compte des distances")],
        compute="_compute_messages")
    street_suiv = fields.Char(compute="compute_prec_suiv_vals")
    zip_suiv = fields.Char(compute="compute_prec_suiv_vals")
    city_suiv = fields.Char(compute="compute_prec_suiv_vals")
    country_suiv_id = fields.Many2one('res.country', compute="compute_prec_suiv_vals")
    geo_lat_suiv = fields.Float(compute="compute_prec_suiv_vals")
    geo_lng_suiv = fields.Float(compute="compute_prec_suiv_vals")
    precision_suiv = fields.Selection(GEO_PRECISION, compute="compute_prec_suiv_vals")

    # Recherche
    distance_max = fields.Integer("Distance max. (km)", default=30, help=u"À vol d'oiseau.")
    secteur_id = fields.Many2one(
        'of.secteur', string="Secteur", help=u"laisser vide pour ne pas restreindre à un secteur en particulier")
    pre_tache_categ_ids = fields.Many2many(
        'of.planning.tache.categ', string=u"Catégories de tâches",
        help=u"Remplir pour restreindre la recherche à certaines catégories de tâches")
    pre_tache_ids = fields.Many2many(
        'of.planning.tache', string=u"Tâches", help=u"Remplir pour restreindre la recherche à certaines tâches")
    ignorer_duree = fields.Boolean(
        string=u"Ignorer durée", help=u"Cochez pour proposer aussi les interventions plus longues que le créneau")

    # Propositions
    proposition_ids = fields.One2many('of.planif.creneau.prop', 'creneau_id', string="propositions")
    proposition_readonly_ids = fields.One2many(related="proposition_ids", readonly=True)
    aucun_res = fields.Boolean(string=u"Aucun résultat!")
    priorite_max = fields.Integer(string=u"Priorité max", help=u"Priorité la plus haute parmis les propositions")
    tout_calcule = fields.Boolean(string=u"réelles toutes calculées", compute="compute_tout_calcule")
    prop_nb = fields.Integer(string=u"Nombre propositionsé", compute="compute_tout_calcule")
    calcule_nb = fields.Integer(string=u"Nombre déjà calculé", compute="compute_tout_calcule")

    # Sélection
    selected_id = fields.Many2one('of.planif.creneau.prop', string="Proposition")
    heure_debut_rdv = fields.Float(string=u'Heure de début', digits=(5, 5))
    duree_rdv = fields.Float(string=u"Durée")
    description_rdv = fields.Text(string='Description')
    employee_other_ids = fields.Many2many('hr.employee', string="Autres intervenants")

    # Autres
    name = fields.Char(compute='_compute_name')
    warning_horaires = fields.Boolean(string="Attention")

    # @api.depends

    @api.depends('date_creneau')
    def _compute_num_jour(self):
        jours_match = {jour.numero: jour.id for jour in self.env['of.jours'].search([])}
        for creneau in self:
            if creneau.date_creneau:
                date_creneau_da = fields.Date.from_string(creneau.date_creneau)
                creneau.num_jour = jours_match[date_creneau_da.isoweekday()]

    @api.depends("creneaux_reels")
    def _compute_creneaux_reels_formatted(self):
        if self.creneaux_reels:
            res_list = []
            creneaux_reels_list = json.loads(self.creneaux_reels)
            for creneau in creneaux_reels_list:
                hours_str_list = hours_to_strs(creneau[0], creneau[1])
                res_list.append("-".join(hours_str_list))
            self.creneaux_reels_formatted = ", ".join(res_list)

    @api.multi
    @api.depends('employee_id.of_address_depart_id', 'employee_id.of_address_retour_id', 'employee_id',
                 'lieu_prec_id', 'lieu_suiv_id')
    def _compute_lieu_depart_arrivee(self):
        for creneau in self:
            if creneau.employee_id.of_address_depart_id == creneau.lieu_prec_id and creneau.lieu_prec_id:
                creneau.lieu_prec_depart = True
            else:
                creneau.lieu_prec_depart = False
            if creneau.employee_id.of_address_retour_id == creneau.lieu_suiv_id and creneau.lieu_suiv_id:
                creneau.lieu_suiv_arrivee = True
            else:
                creneau.lieu_suiv_arrivee = False

    @api.multi
    @api.depends('lieu_prec_id', 'lieu_prec_manual_id', 'lieu_suiv_id', 'lieu_suiv_manual_id')
    def _compute_messages(self):
        for creneau in self:
            message_lieu_prec = not creneau.lieu_prec_id.geo_lat and not creneau.lieu_prec_manual_id.geo_lat
            message_lieu_suiv = not creneau.lieu_suiv_id.geo_lat and not creneau.lieu_suiv_manual_id.geo_lat

            if message_lieu_prec and message_lieu_suiv:  # probleme avec les lieux précédent et suivant
                creneau.lieu_prec_message = False
                creneau.lieu_suiv_message = 'lieu_prec_suiv_prob'
            elif message_lieu_prec:
                creneau.lieu_suiv_message = False
                if not creneau.lieu_prec_id and not creneau.lieu_prec_manual_id:
                    creneau.lieu_prec_message = 'lieu_prec_absent'
                else:
                    creneau.lieu_prec_message = 'lieu_prec_non_geoloc'
            elif message_lieu_suiv:
                creneau.lieu_prec_message = False
                if not creneau.lieu_suiv_id and not creneau.lieu_suiv_manual_id:
                    creneau.lieu_suiv_message = 'lieu_suiv_absent'
                else:
                    creneau.lieu_suiv_message = 'lieu_suiv_non_geoloc'
            else:
                creneau.lieu_prec_message = False
                creneau.lieu_suiv_message = False

    @api.multi
    @api.depends('lieu_prec_id', 'lieu_prec_manual_id', 'lieu_suiv_id', 'lieu_suiv_manual_id')
    def compute_prec_suiv_vals(self):
        for wizard in self:
            if wizard.lieu_prec_manual_id:
                wizard.street_prec = wizard.lieu_prec_manual_id.street
                wizard.zip_prec = wizard.lieu_prec_manual_id.zip and wizard.lieu_prec_manual_id.zip + u", " or u""
                wizard.city_prec = wizard.lieu_prec_manual_id.city and wizard.lieu_prec_manual_id.city + u", " or u""
                wizard.country_prec_id = wizard.lieu_prec_manual_id.country_id.id
                wizard.geo_lat_prec = wizard.lieu_prec_manual_id.geo_lat
                wizard.geo_lng_prec = wizard.lieu_prec_manual_id.geo_lng
                wizard.precision_prec = wizard.lieu_prec_manual_id.precision
            else:
                wizard.street_prec = wizard.lieu_prec_id.street
                wizard.zip_prec = wizard.lieu_prec_id.zip and wizard.lieu_prec_id.zip + u", " or u""
                wizard.city_prec = wizard.lieu_prec_id.city and wizard.lieu_prec_id.city + u", " or u""
                wizard.country_prec_id = wizard.lieu_prec_id.country_id.id
                wizard.geo_lat_prec = wizard.lieu_prec_id.geo_lat
                wizard.geo_lng_prec = wizard.lieu_prec_id.geo_lng
                wizard.precision_prec = wizard.lieu_prec_id.precision
            if wizard.lieu_suiv_manual_id:
                wizard.street_suiv = wizard.lieu_suiv_manual_id.street
                wizard.zip_suiv = wizard.lieu_suiv_manual_id.zip and wizard.lieu_suiv_manual_id.zip + u", " or u""
                wizard.city_suiv = wizard.lieu_suiv_manual_id.city and wizard.lieu_suiv_manual_id.city + u", " or u""
                wizard.country_suiv_id = wizard.lieu_suiv_manual_id.country_id.id
                wizard.geo_lat_suiv = wizard.lieu_suiv_manual_id.geo_lat
                wizard.geo_lng_suiv = wizard.lieu_suiv_manual_id.geo_lng
                wizard.precision_suiv = wizard.lieu_suiv_manual_id.precision
            else:
                wizard.street_suiv = wizard.lieu_suiv_id.street
                wizard.zip_suiv = wizard.lieu_suiv_id.zip and wizard.lieu_suiv_id.zip + u", " or u""
                wizard.city_suiv = wizard.lieu_suiv_id.city and wizard.lieu_suiv_id.city + u", " or u""
                wizard.country_suiv_id = wizard.lieu_suiv_id.country_id.id
                wizard.geo_lat_suiv = wizard.lieu_suiv_id.geo_lat
                wizard.geo_lng_suiv = wizard.lieu_suiv_id.geo_lng
                wizard.precision_suiv = wizard.lieu_suiv_id.precision

    @api.multi
    @api.depends('proposition_ids', 'proposition_ids.fait')
    def compute_tout_calcule(self):
        for wizard in self:
            if not wizard.proposition_ids:
                wizard.tout_calcule = True
                wizard.calcule_nb = 0
                wizard.prop_nb = 0
            else:
                pas_fait = wizard.proposition_ids.filtered(lambda prop: not prop.fait)
                wizard.tout_calcule = not pas_fait
                wizard.calcule_nb = len(wizard.proposition_ids) - len(pas_fait)
                wizard.prop_nb = len(wizard.proposition_ids)

    @api.multi
    @api.depends('employee_id', 'heure_debut_creneau', 'heure_fin_creneau')
    def _compute_name(self):
        for creneau in self:
            creneau.name = u'%s : Créneau %s' % ((creneau.employee_id.name or u''),
                                                 (creneau.creneaux_reels_formatted or u''))

    @api.onchange('pre_tache_categ_ids')
    def onchange_pre_tache_categ_ids(self):
        # remplir les taches en fonction des catégories
        self.ensure_one()
        if self.pre_tache_categ_ids:
            tache_ids = self.pre_tache_categ_ids.mapped('tache_ids')
            self.pre_tache_ids = [(5,)] + [(4, tache_id) for tache_id in tache_ids.ids]

    # @api.onchange

    @api.onchange('selected_id')
    def onchange_selected_id(self):
        self.ensure_one()
        if self.selected_id:
            self.description_rdv = self.selected_id.service_id.note

    # Actions

    @api.multi
    def reload_wizard(self):
        action = self.env.ref('of_planning_view.action_view_of_planif_wizard').read()[0]
        action['context'] = self._context
        action['res_id'] = self.id
        return action

    @api.multi
    def button_compute_more(self):
        prop_a_faire = self.proposition_ids.filtered(lambda prop: not prop.fait)[:25]
        prop_a_faire.compute_distance_reelle()
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_search(self):
        self.set_proposition_ids()
        self.set_selected_id()
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_select(self, prop_id):
        """Sélectionne cette proposition comme résultat"""
        self.ensure_one()
        self.selected_id.selected = False
        prop = self.env['of.planif.creneau.prop'].browse(prop_id)
        prop.selected = True
        self.duree_rdv = prop.service_id.duree
        self.selected_id = prop.id
        self.onchange_selected_id()
        return self.reload_wizard()

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        if not self.duree_rdv:
            raise UserError(u"Avez-vous pensé à vérifier la durée de votre intervention?")
        intervention = self.create_intervention()
        if self.selected_id.service_id.recurrence:
            date_next = intervention.service_id.get_next_date(self.date_creneau)
            intervention.service_id.write({
                'date_next': date_next,
                'date_fin': intervention.service_id.get_fin_date(date_next)
            })
        return

    @api.multi
    def button_confirm_next(self):
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        if not self.duree_rdv:
            raise UserError(u"Avez-vous pensé à vérifier la durée de votre intervention?")
        intervention = self.create_intervention()
        intervention._compute_date_deadline()
        date_dt = fields.Datetime.from_string(intervention.date)
        date_deadline_dt = fields.Datetime.from_string(intervention.date_deadline)
        same_day = (date_deadline_dt - date_dt).days == 0
        duree_min = self.env['ir.values'].get_default('of.intervention.settings', 'duree_min_creneaux_dispo')
        self.duree_creneau -= intervention.duree
        if self.duree_creneau < duree_min:
            same_day = False  # pour passer le recalcul des créneaux
            creneau_fini = True
        else:
            creneau_fini = False

        if same_day:
            # On réinitialise les champs du wizard pour lancer une nouvelle recherche
            date_fin_interv_locale_dt = fields.Datetime.context_timestamp(
                self, fields.Datetime.from_string(intervention.date_deadline))
            interv_heure_fin = round(date_fin_interv_locale_dt.hour +
                                     date_fin_interv_locale_dt.minute / 60.0 +
                                     date_fin_interv_locale_dt.second / 3600.0, 5)
            creneaux = json.loads(self.creneaux_reels)
            for i in xrange(len(creneaux)):
                creneau = creneaux[i]
                if creneau[0] <= interv_heure_fin <= creneau[1]:
                    # trouvé!
                    if float_compare(interv_heure_fin, creneau[1], 5) == 0:
                        # Le créneau a été entièrement rempli: on le supprime
                        if i < len(creneaux) - 1:
                            # Il reste d'autres créneaux à planifier ce jour
                            creneaux = creneaux[i + 1:]
                        else:
                            # La journée est totalement planifiée
                            creneau_fini = True
                        break
                    else:
                        # La nouvelle heure de début du créneau est l'heure de fin de l'intervention
                        creneaux = creneaux[i:]
                        creneaux[0][0] = interv_heure_fin
                        break
            else:
                raise UserError(
                    u"On dirait que cette journée est entièrement planifiée pour %s" % self.employee_id.name)
        if creneau_fini:  # le créneau est entièrement planifié!
            self.creneau_fini = creneau_fini
        else:
            # mise à jour des données du créneau
            self.creneaux_reels = json.dumps(creneaux)

            self.priorite_max = 0
            self.lieu_prec_id = intervention.address_id
            self.proposition_ids.unlink()
            self.heure_debut_creneau = creneaux[0][0]
            self.heure_debut_rdv = creneaux[0][0]

            self.set_proposition_ids()
            self.set_selected_id()
        if self._context.get('from_prop', False):
            return self.reload_wizard()
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_close(self):
        return

    # Autres

    @api.multi
    def set_proposition_ids(self):
        self.ensure_one()
        vals_list = self.get_candidats()
        la_list = [(5, 0, 0)] + [(0, 0, values) for values in vals_list]

        self.proposition_ids = la_list

    @api.multi
    def get_candidats(self):
        self.ensure_one()

        un_mois = relativedelta(months=1)
        une_semaine = relativedelta(weeks=1)
        date_creneau_da = fields.Date.from_string(self.date_creneau)
        date_un_mois_da = date_creneau_da + un_mois
        date_1_semaine_da = date_creneau_da + une_semaine
        date_2_semaines_da = date_creneau_da + 2 * une_semaine
        date_un_mois_str = fields.Date.to_string(date_un_mois_da)
        date_1_semaine_str = fields.Date.to_string(date_1_semaine_da)
        date_2_semaines_str = fields.Date.to_string(date_2_semaines_da)
        taches_possibles = self.employee_id.get_taches_possibles()
        if not self.ignorer_duree:
            # seulement les taches suffisamment courtes a prendre en compte
            taches_possibles = taches_possibles.filtered(lambda t: t.duree <= self.duree_creneau)
        if self.pre_tache_ids:
            taches_possibles = taches_possibles.filtered(lambda t: t.id in self.pre_tache_ids.ids)

        vals_list = []
        service_domain = [
            '|', ('jour_ids', 'in', self.num_jour),
                 ('jour_ids', '=', False),  # les jours peuvent ne pas être renseignés
            ('tache_id', 'in', taches_possibles.ids),
            ('date_next', '<=', date_un_mois_str),  # ne pas proposer d'interventions à programmer dans plus d'un mois
            '|', ('recurrence', '=', False),
                 '|', ('date_fin_contrat', '=', False),
                      ('date_fin_contrat', '>', self.date_creneau),
        ]
        if self.secteur_id:
            # dans le cas ou le secteur n'est pas renseigné, on regarde les codes postaux
            for zip_range in self.secteur_id.zip_range_ids:
                if zip_range.cp_min == zip_range.cp_max:
                    service_domain.append('|')
                    service_domain.append(('address_zip', '=', zip_range.cp_min))
                else:
                    service_domain.append('|')
                    service_domain.append('&')
                    service_domain.append(('address_zip', '>=', zip_range.cp_min))
                    service_domain.append(('address_zip', '<=', zip_range.cp_max))
            service_domain.append(('secteur_tech_id', '=', self.secteur_id.id))
            # exclusion des secteurs intérieurs
            secteurs_interieurs = self.secteur_id.get_secteurs_interieurs('tech')
            if secteurs_interieurs:
                zip_range_excluded = secteurs_interieurs.mapped('zip_range_ids')
                for zip_range in zip_range_excluded:
                    if zip_range.cp_min == zip_range.cp_max:
                        service_domain.append(('address_zip', '!=', zip_range.cp_min))
                    else:
                        service_domain.append('|')
                        service_domain.append(('address_zip', '<', zip_range.cp_min))
                        service_domain.append(('address_zip', '>', zip_range.cp_max))
                service_domain.append(('address_zip', 'not in', zip_range_excluded.ids))  # à corriger
        # services
        services = self.env['of.service'].search(service_domain).filter_state_poncrec_date(date_eval=self.date_creneau)
        distance_max = self.distance_max * 1.3  # approximation
        priorite_max = 0
        lieu_prec = self.lieu_prec_manual_id or self.lieu_prec_id
        lieu_suiv = self.lieu_suiv_manual_id or self.lieu_suiv_id
        calcul_distance_oiseau = True
        if not lieu_prec and not lieu_suiv:
            calcul_distance_oiseau = False
        elif not lieu_prec:
            lieu_prec = lieu_suiv
        elif not lieu_suiv:
            lieu_suiv = lieu_prec

        for service in services:
            priorite = 0
            # priorité par spatialité
            if calcul_distance_oiseau:
                voloiseau_prec = voloiseau(service.geo_lat, service.geo_lng, lieu_prec.geo_lat, lieu_prec.geo_lng)
                voloiseau_suiv = voloiseau(service.geo_lat, service.geo_lng, lieu_suiv.geo_lat, lieu_suiv.geo_lng)
                if voloiseau_prec > distance_max:  # trop loins
                    continue
                if voloiseau_suiv > distance_max:
                    continue
                if voloiseau_prec + voloiseau_suiv <= 5:
                    priorite += 3
                elif voloiseau_prec + voloiseau_suiv <= 10:
                    priorite += 2
                elif voloiseau_prec + voloiseau_suiv <= 15:
                    priorite += 1
            # priorité par temporalité
            if service.date_fin < self.date_creneau:  # en retard!
                priorite += 3
            elif service.date_fin <= date_1_semaine_str:  # à faire cette semaine
                priorite += 2
            elif service.date_fin <= date_2_semaines_str:  # à faire cette quinzaine
                priorite += 1

            if priorite > priorite_max:
                priorite_max = priorite

            vals = {
                'priorite': priorite,
                'service_id': service.id,
                'date_next': service.date_next,
                'date_fin': service.date_fin,
            }
            vals_list.append(vals)
        self.priorite_max = priorite_max

        return vals_list

    @api.multi
    def set_selected_id(self):
        self.ensure_one()
        if not self.proposition_ids:
            self.selected_id = False
            self.aucun_res = True
            return
        prop_selected = self.proposition_ids.filtered(lambda p: p.selected)
        if prop_selected:
            prop_selected.selected = False
        self.proposition_ids.compute_distance_reelle()
        prop_a_supr = self.proposition_ids.filtered(lambda p: p.distance_reelle_tota > self.distance_max)
        self.proposition_ids -= prop_a_supr
        prop_a_supr.unlink()
        self.selected_id = self.proposition_ids.get_closer_one()
        if self.selected_id:
            self.selected_id.selected = True
            self.duree_rdv = self.selected_id.service_id.duree
            self.description_rdv = self.selected_id.service_id.note
            self.aucun_res = False
        else:
            self.aucun_res = True

    @api.multi
    def get_values_intervention_create(self):
        self.ensure_one()

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        service = self.selected_id.service_id
        date_da = fields.Date.from_string(self.date_creneau)
        date_propos_dt = datetime.combine(date_da, datetime.min.time()) + timedelta(
            hours=self.heure_debut_rdv)  # datetime naive
        date_propos_dt = tz.localize(date_propos_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc
        employee_ids = [self.employee_id.id] + self.employee_other_ids.ids

        values = {
            'partner_id': service.partner_id.id,
            'address_id': service.address_id.id,
            'tache_id': service.tache_id.id,
            'service_id': service.id,
            'employee_ids': [(6, 0, employee_ids)],
            'date': fields.Datetime.to_string(date_propos_dt),
            'duree': self.duree_rdv,
            'user_id': self._uid,
            'company_id': service.address_id.company_id and service.address_id.company_id.id,
            'name': service.name,
            'description': self.description_rdv or '',
            'state': 'confirm',
            'verif_dispo': True,
            'order_id': service.order_id.id,
            'origin_interface': u"Remplir un créneau (wizard planif)",
        }

        return values

    @api.multi
    def create_intervention(self):
        self.ensure_one()
        intervention_vals = self.get_values_intervention_create()
        return self.env['of.planning.intervention'].create(intervention_vals)


class OfPlanifCreneauProp(models.TransientModel):
    _name = 'of.planif.creneau.prop'
    _description = u"Proposition d'intervention à programmer"
    _order = "creneau_id DESC, selected DESC, priorite DESC, distance_arrondi_order, date_next, date_fin," \
             " distance_order"

    # Champs

    service_id = fields.Many2one("of.service", string="Service")
    creneau_id = fields.Many2one('of.planif.creneau', string=u"Créneau")

    # Titre
    employee_name = fields.Char(related="creneau_id.employee_id.name", readonly=True)

    # Rubrique Partenaire
    partner_id = fields.Many2one(related="service_id.partner_id")
    address_id = fields.Many2one(related="service_id.address_id")
    address_street = fields.Char(related="service_id.address_id.street", readonly=True)
    address_zip = fields.Char('Code Postal', size=24, related='service_id.address_id.zip', readonly=True)
    address_city = fields.Char('Ville', related='service_id.address_id.city', readonly=True)
    address_country_id = fields.Many2one(related="service_id.address_id.country_id", readonly=True)
    partner_of_telephones = fields.Text(related='service_id.partner_id.of_telephones', readonly=True)

    # Rubrique Mémo
    date_next = fields.Date(string=u"À planifier entre le", readonly=True)
    date_fin = fields.Date(string="et le", readonly=True)
    origin = fields.Char(related="service_id.origin", readonly=True)
    distance_reelle_prec = fields.Float(string=u'Distance du précédent', digits=(5, 2), help=u"Réelle")
    distance_reelle_suiv = fields.Float(string=u'Distance du suivant', digits=(5, 2), help=u"Réelle")
    distance_reelle_tota = fields.Float(string=u'Distance totale (km)', digits=(5, 2), help=u"Réelle", default=-1)

    # Rubrique Planification
    selected = fields.Boolean(string=u"Sélectionné")
    heure_debut_rdv = fields.Float(related='creneau_id.heure_debut_rdv')
    duree_rdv = fields.Float(related='creneau_id.duree_rdv')
    duree_restante = fields.Float(related='service_id.duree_restante', readonly=True)
    employee_other_ids = fields.Many2many('hr.employee', related='creneau_id.employee_other_ids')
    tache_name = fields.Char(related='service_id.tache_id.name', string="Prestation", readonly=True)

    # Rubrique Description
    description_rdv = fields.Text(related='creneau_id.description_rdv')

    # Vue liste
    fait = fields.Boolean(string=u"déjà calculé")
    priorite = fields.Integer(string=u"Priorité")
    partner_name = fields.Char(string="Client", related='service_id.partner_id.name', readonly=True)
    distance_oiseau_prec = fields.Float(
        string=u'Distance du précédent', digits=(5, 5), compute="_compute_distance_oiseau", help=u"À vol d'oiseau")
    distance_oiseau_suiv = fields.Float(
        string=u'Distance du suivant', digits=(5, 5), compute="_compute_distance_oiseau", help=u"À vol d'oiseau")
    osrm_response = fields.Text(string=u"Réponse OSRM")
    distance_order = fields.Float(
        string=u'Distance totale order', digits=(5, 2), help=u"pour ordonner", default="99999")
    distance_arrondi_order = fields.Float(
        string=u'Distance arrondi order', digits=(5, 2), help=u"pour ordonner", default="99999")

    # Autres
    geo_lat = fields.Float(related='service_id.geo_lat', readonly=True)
    geo_lng = fields.Float(related='service_id.geo_lng', readonly=True)
    precision = fields.Selection(related='service_id.precision', readonly=True)

    # @api.dpends

    @api.multi
    @api.depends('geo_lat', 'geo_lng', 'creneau_id')
    def _compute_distance_oiseau(self):
        for a_planifier in self:
            if a_planifier.geo_lat == 0.0 or a_planifier.geo_lng == 0.0:
                a_planifier.distance_oiseau_prec = -1
                a_planifier.distance_oiseau_suiv = -1
                continue
            if a_planifier.creneau_id.geo_lat_prec == 0.0 or a_planifier.creneau_id.geo_lng_prec == 0.0:
                a_planifier.distance_oiseau_prec = -1
            else:
                a_planifier.distance_oiseau_prec = voloiseau(
                    a_planifier.geo_lat, a_planifier.geo_lng, a_planifier.creneau_id.geo_lat_prec,
                    a_planifier.creneau_id.geo_lng_prec)
            if a_planifier.creneau_id.geo_lat_suiv == 0.0 or a_planifier.creneau_id.geo_lng_suiv == 0.0:
                a_planifier.distance_oiseau_suiv = -1
            else:
                a_planifier.distance_oiseau_suiv = voloiseau(
                    a_planifier.geo_lat, a_planifier.geo_lng, a_planifier.creneau_id.geo_lat_suiv,
                    a_planifier.creneau_id.geo_lng_suiv)

    # @api.onchange

    @api.multi
    @api.onchange('heure_debut_rdv')
    def onchange_heure_debut_rdv(self):
        self.ensure_one()
        # veŕifier que l'heure de début choisie est sur les créneaux proposés
        for i in range(len(self.creneau_id.creneaux_reels)):
            # début sur créneau
            if self.creneau_id.creneaux_reels[i][0] <= self.heure_debut_rdv < self.creneau_id.creneaux_reels[i][1]:
                break
        else:
            raise UserError(u"l'heure de début choisi est en dehors de ce créneau.\n"
                            u"Pour votre information, les horaires de ce créneau sont :\n"
                            u"%s" % self.creneau_id.creneaux_reels_formatted)

    @api.multi
    @api.onchange('selected')
    def onchange_selected(self):
        self.ensure_one()
        if self.selected and self.creneau_id.selected_id.id != self.id:
            self.creneau_id.selected_id.selected = False
            self.creneau_id.selected_id = self.id
            self.description_rdv = self.service_id.note

    @api.onchange('fait')
    def onchange_fait(self):
        self.ensure_one()
        self.creneau_id.proposition_ids.compute_distance_reelle()

    # Actions

    @api.multi
    def button_select(self):
        """Sélectionne cette proposition comme résultat"""
        self.ensure_one()
        self.creneau_id.selected_id.selected = False
        self.selected = True
        self.creneau_id.duree_rdv = self.service_id.duree
        self.creneau_id.selected_id = self.id
        self.creneau_id.onchange_selected_id()
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_select_from_list(self):
        """Sélectionne cette proposition comme résultat"""
        self.ensure_one()
        return self.creneau_id.button_select(self.id)

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        return self.creneau_id.button_confirm()

    @api.multi
    def button_confirm_next(self):
        self.ensure_one()
        self = self.with_context(from_prop=True)
        return self.creneau_id.button_confirm_next()

    # Autres

    @api.multi
    def compute_distance_reelle(self):
        """Interroge le serveur OSRM openfire pour calculer les distances réelles"""
        self = self.filtered('creneau_id')
        if not self:
            return
        creneau = self[0].creneau_id
        lieu_prec = creneau.lieu_prec_manual_id or creneau.lieu_prec_id
        lieu_suiv = creneau.lieu_suiv_manual_id or creneau.lieu_suiv_id
        if not lieu_prec and not lieu_suiv:
            self.update({
                'distance_reelle_prec': -1,
                'distance_reelle_suiv': -1,
                'distance_reelle_tota': -1,
                'distance_order': 99999,
                'distance_arrondi_order': 99999,
                'osrm_response': "",
            })
            return
        if not lieu_prec:
            lieu_prec = lieu_suiv
        elif not lieu_suiv:
            lieu_suiv = lieu_prec
        geo_lat_prec = lieu_prec.geo_lat
        geo_lng_prec = lieu_prec.geo_lng
        geo_lat_suiv = lieu_suiv.geo_lat
        geo_lng_suiv = lieu_suiv.geo_lng
        compteur = 0
        routing_base_url = config.get("of_routing_base_url", "")
        routing_version = config.get("of_routing_version", "")
        routing_profile = config.get("of_routing_profile", "")

        for indice in range(len(self)):
            a_planifier = self[indice]

            if a_planifier.fait:
                continue
            if compteur >= 25:
                # Ne pas calculer plus de 25 d'un coup pour éviter les lenteurs
                break

            if not (routing_base_url and routing_version and routing_profile):
                continue
            else:
                query = routing_base_url + "route/" + routing_version + "/" + routing_profile + "/"
            # Listes de coordonnées : ATTENTION OSRM prend ses coordonnées sous form (lng, lat)
            # lieu précédent
            coords_str = str(geo_lng_prec) + "," + str(geo_lat_prec)
            # lieu de l'intervention à programmer
            coords_str += ";" + str(a_planifier.geo_lng) + "," + str(a_planifier.geo_lat)
            # lieu suivant
            coords_str += ";" + str(geo_lng_suiv) + "," + str(geo_lat_suiv)
            query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
            full_query = query_send + coords_str + "?"
            try:
                req = requests.get(full_query)
                res = req.json()
            except Exception:
                res = {}

            if res and res.get('routes'):
                legs = res['routes'][0]['legs']
                dist_prec = round(legs[0][u'distance'] / 1000.0, 2)
                dist_suiv = round(legs[1][u'distance'] / 1000.0, 2)
                a_planifier.distance_reelle_prec = dist_prec
                a_planifier.distance_reelle_suiv = dist_suiv
                a_planifier.distance_reelle_tota = dist_prec + dist_suiv
                a_planifier.distance_order = dist_prec + dist_suiv
                a_planifier.distance_arrondi_order = arrondi_sup(dist_prec + dist_suiv, 5)
                a_planifier.osrm_response = legs
                a_planifier.fait = True
            else:
                a_planifier.distance_reelle_prec = -1
                a_planifier.distance_reelle_suiv = -1
                a_planifier.distance_reelle_tota = -1
                a_planifier.distance_order = 99999
                a_planifier.distance_arrondi_order = 99999
                a_planifier.osrm_response = res
                a_planifier.fait = True
            compteur += 1

    @api.multi
    def get_closer_one(self):
        """Renvoie la proposition dont la distance réelle est la plus petite parmi les éléments de self
           ordonnés par priorite DESC, distance_arrondi_order, date_next, date_fin, distance_order"""
        min_prop = False
        if not len(self):
            return False
        creneau = self[0].creneau_id
        lieu_prec = creneau.lieu_prec_manual_id or creneau.lieu_prec_id
        lieu_suiv = creneau.lieu_suiv_manual_id or creneau.lieu_suiv_id
        if not (lieu_prec or lieu_suiv):
            return self[0]
        propositions = self.filtered(lambda p: p.distance_order < 99000)
        while not propositions:
            self.compute_distance_reelle()
            propositions = self.filtered(lambda p: p.distance_order < 99000)
        for prop in propositions:
            if not min_prop:  # initialisation min_prop
                min_prop = prop
            elif prop.priorite < min_prop.priorite:
                min_prop = prop
            elif prop.priorite > min_prop.priorite:
                continue
            elif prop.distance_arrondi_order < min_prop.distance_arrondi_order:
                min_prop = prop
            elif prop.distance_arrondi_order > min_prop.distance_arrondi_order:
                continue
            elif prop.date_next < min_prop.date_next:
                min_prop = prop
            elif prop.date_next > min_prop.date_next:
                continue
            elif prop.date_fin < min_prop.date_fin:
                min_prop = prop
            elif prop.date_fin > min_prop.date_fin:
                continue
            elif prop.distance_order < min_prop.distance_order:
                min_prop = prop
            elif prop.distance_order > min_prop.distance_order:
                continue

        return min_prop


class OfPlanifCreneauSecteur(models.TransientModel):
    _name = 'of.planif.creneau.secteur'
    _description = u'Assigner un secteur à un créneau disponible'

    secteur_id = fields.Many2one(
        'of.secteur', string="Secteur", help="Laisser vide pour retirer l'assignation de secteur")
    employee_id = fields.Many2one('hr.employee', string="Intervenant", readonly=True)
    date_creneau = fields.Date(string=u"Date du créneau", readonly=True)

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        tournee_obj = self.env['of.planning.tournee']
        tournee = tournee_obj.search(
            [('employee_id', '=', self.employee_id.id),
             ('date', '=', self.date_creneau)], limit=1)
        if tournee:
            tournee.secteur_id = self.secteur_id
        elif self.secteur_id:
            vals = {
                'employee_id': self.employee_id.id,
                'date': self.date_creneau,
                'secteur_id': self.secteur_id.id,
            }
            tournee_obj.create(vals)
        return

    @api.multi
    def button_cancel(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
