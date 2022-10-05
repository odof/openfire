# -*- coding: utf-8 -*-

from odoo.osv import orm
from odoo.tools.float_utils import float_compare
from odoo import models, fields, api
from odoo.addons.of_utils.models.of_utils import hours_to_strs
from odoo.exceptions import ValidationError

import pytz
from datetime import datetime, timedelta

PLANNING_VIEW = ('planning', 'Planning')


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def get_infos_lieu(self):
        """Retourne un dictionnaire de valeurs contenant l'adresse et les données de géoloc"""
        self.ensure_one()
        res = {
            'geo_lat': self.geo_lat,
            'geo_lng': self.geo_lng,
            'precision': self.precision,
            'city': self.city,
            'zip': self.zip,
            'id': self.id,
            'country': self.get_geocoding_country(),
            'name': self.name,
            }
        return res


class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _inherit = ["of.planning.intervention", "of.readgroup", "of.calendar.mixin"]

    employee_names = fields.Char(string="Noms des intervenants", compute='_compute_employee_names')
    tag_names = fields.Char(string=u"Noms des étiquettes", compute='_compute_tag_names')
    tooltip_description = fields.Text(string="Description survol", compute='_compute_tooltip_description')

    @api.depends('employee_ids', 'employee_ids.name')
    def _compute_employee_names(self):
        for rdv in self:
            employees = rdv.employee_ids.filtered('name')
            rdv.employee_names = ', '.join(employees.mapped('name'))

    @api.depends('tag_ids', 'tag_ids.name')
    def _compute_tag_names(self):
        for rdv in self:
            tags = rdv.tag_ids.filtered('name')
            rdv.tag_names = ', '.join(tags.mapped('name'))

    @api.depends('description')
    def _compute_tooltip_description(self):
        for rdv in self:
            description = rdv.description or ''
            rdv.tooltip_description = description[:400]

    @api.model
    def get_creneaux_dispo(self, employee_id, date, intervention_heures, creneaux_travailles,
                           duree_min, intervention_forcee, fusion_creneaux=True):
        """
        Similaire au calcul de créneaux dispo de rdv.py.
        L'idée ici est de fusionner les créneaux dispos consécutifs.
        exple: une journée sans intervention programmée ne doit avoir qu'un créneau dispo
        :param employee_id: id de l'employé dont on cherche les créneaux dispos
        :param date: string date à évaluer
        :param intervention_heures: listes de tuples (intervention, heure_debut, heure_fin)
        :param creneaux_travailles: listes de tuples (heure_debut, heure_fin)
        :param duree_min: durée minimale pour qu'un créneau soit considéré comme dispo
        :param intervention_forcee: True si au moins un RDV a ses dates forcées
        :param fusion_creneaux: True si on veut fusionner les créneaux libres qui se succèdent sans intervention
        :return: liste de créneaux dispos fusionnés
        """
        if not creneaux_travailles:
            return []
        compare_precision = 5
        employee = self.env['hr.employee'].browse(int(employee_id))
        creneaux = []
        lieu_depart = employee.of_address_depart_id and employee.of_address_depart_id.get_infos_lieu() or False
        lieu_retour = employee.of_address_retour_id and employee.of_address_retour_id.get_infos_lieu() or False
        tournee = self.env['of.planning.tournee'].search([('date', '=', date), ('employee_id', '=', employee_id)],
                                                         limit=1)
        date_da = fields.Date.from_string(date)
        tz = pytz.timezone(self._context.get('tz', 'Europe/Paris'))

        if tournee:
            secteur = tournee.secteur_id
            # les lieux de départ et de retour d'une tournée priment sur ceux de l'employé
            lieu_depart = tournee.address_depart_id and tournee.address_depart_id.get_infos_lieu() or lieu_depart
            lieu_retour = tournee.address_retour_id and tournee.address_retour_id.get_infos_lieu() or lieu_retour
        else:
            secteur = False
        secteur_str = secteur and secteur.name or ""

        creneau_ind = 0
        creneau = creneaux_travailles[0]
        # heure_debut est l'heure à partir de laquelle on peut commencer à définir un créneau disponible.
        # Il s'agit soit de l'heure de début d'un créneau, soit le l'heure de fin de la dernière intervention étudiée.
        heure_debut = creneau[0]
        display_secteur = not intervention_heures
        for interv, interv_debut, interv_fin in intervention_heures + [(False, 24, 24)]:
            # Pour chaque intervention, on enregistre les créneaux qui se terminent avant le début de l'intervention

            while creneau and creneau[1] <= heure_debut:
                # Le créneau en cours est terminé, on passe au créneau suivant
                creneau_ind += 1
                creneau = creneaux_travailles[creneau_ind] if creneau_ind < len(creneaux_travailles) else False
                if creneau:
                    heure_debut = max(heure_debut, creneau[0])
            if not creneau:
                break

            creneaux_reels = []
            lieu_fin = interv.address_id and interv.address_id.get_infos_lieu() or False if interv else lieu_retour
            while True:
                # if creneau and creneau[1] < interv_debut:
                if creneau and float_compare(creneau[1], interv_debut, compare_precision) == -1:
                    # Le créneau se termine avant le début de l'intervention
                    # on l'inclut dans le temps disponible et on passe au créneau suivant
                    creneaux_reels.append((max(heure_debut, creneau[0]), creneau[1]))
                    creneau_ind += 1
                    creneau = creneaux_travailles[creneau_ind] if creneau_ind < len(creneaux_travailles) else False
                    continue

                # Le créneau est coupé par l'intervention ou commence après celle-ci
                # if creneau[0] < interv_debut:
                if creneau and float_compare(creneau[0], interv_debut, compare_precision) == -1:
                    # Le créneau est coupé par l'intervention
                    creneaux_reels.append((max(heure_debut, creneau[0]), interv_debut))
                # On retire les créneaux vides
                # Survient quand un horaire de 0 minutes a été saisi pour l'employé
                #    ou quand deux interventions se suivent sur un créneau
                creneaux_reels = [creneau_reel for creneau_reel in creneaux_reels
                                  if float_compare(creneau_reel[0], creneau_reel[1], compare_precision) == -1]
                duree_creneau = sum(hor[1] - hor[0] for hor in creneaux_reels)
                # Ajouter le créneau seulement si sa durée est au moins égale à la durée min autorisée

                if fusion_creneaux and creneaux_reels and \
                        float_compare(duree_creneau, duree_min, compare_precision) != -1:
                    creneaux.append({
                        'attendee_name': employee.name,
                        'heure_debut': heure_debut,
                        'heure_fin': creneaux_reels[-1][1],
                        'lieu_debut': lieu_depart,
                        'lieu_fin': lieu_fin,
                        'duree': duree_creneau,
                        'creneaux_reels': creneaux_reels,
                        'secteur_id': secteur and secteur.id or False,
                        'secteur_str': secteur_str,
                        'display_secteur': display_secteur,
                        'warning_horaires': intervention_forcee,
                    })
                else:
                    for cren in creneaux_reels:
                        date_deb_locale_dt = datetime.combine(date_da, datetime.min.time()) + timedelta(
                            hours=cren[0])
                        date_deb_utc_dt = tz.localize(date_deb_locale_dt, is_dst=None).astimezone(pytz.utc)
                        date_fin_locale_dt = datetime.combine(date_da, datetime.min.time()) + timedelta(
                            hours=cren[1])
                        date_fin_utc_dt = tz.localize(date_fin_locale_dt, is_dst=None).astimezone(pytz.utc)
                        to_append = {
                            'attendee_name': employee.name,
                            'date_prompt': fields.Datetime.to_string(date_deb_utc_dt),
                            'date_deadline_prompt': fields.Datetime.to_string(date_fin_utc_dt),
                            'heure_debut': cren[0],
                            'heure_fin': cren[1],
                            'lieu_debut': lieu_depart,
                            'lieu_fin': lieu_fin,
                            'duree': cren[1] - cren[0],
                            'creneaux_reels': creneaux_reels,
                            'secteur_id': secteur and secteur.id or False,
                            'secteur_str': secteur_str,
                            'display_secteur': display_secteur,
                            'warning_horaires': intervention_forcee,
                            'defaults': {'employee_ids': [employee_id]},
                        }
                        creneaux.append(to_append)
                break

            heure_debut = interv_fin
            lieu_depart = lieu_fin
            if interv and not tournee:
                secteur = interv.secteur_id or secteur
                secteur_str = secteur and secteur.name or ""

        return creneaux

    @api.model
    def pause_interv(self, heures_interv, creneaux):
        """
        Renvoie la durée de pause entre le début et la fin d'une intervention.
        Ne fonctionne pas pour les interventions sur plusieurs jours à l'heure actuelle.
        Principe: On trouve le créneau de début de l'intervention ainsi que celui de fin.
        Puis on fait la somme des pauses entre ces créneaux.
        :param heures_interv: Tuple (heure_debut, heure_fin)
        :param creneaux: liste des créneaux travaillés de la journée exemple: [(8, 12), (14, 18)]
        :return: Float temps de pause en heures
        """
        heure_debut = heures_interv[0]
        heure_fin = heures_interv[1]
        index_debut = 0
        index_fin = len(creneaux) - 1
        temps_chevauche = 0.0
        # trouver le créneau de début du RDV
        for i in range(len(creneaux)):
            creneau_courant = creneaux[i]
            if creneau_courant[0] <= heure_debut <= creneau_courant[1]:
                index_debut = i
                break
        # trouver le créneau de fin du RDV
        for i in range(index_debut, len(creneaux)):
            creneau_courant = creneaux[i]
            if creneau_courant[0] <= heure_fin <= creneau_courant[1]:
                index_fin = i
                break
        # Somme des temps de pauses entre le créneau de début et celui de fin
        while index_debut < index_fin:
            temps_chevauche += (creneaux[index_debut + 1][0] - creneaux[index_debut][1])
            index_debut += 1
        return temps_chevauche

    @api.model
    def get_display_data(
            self, employee_ids, date_start, date_stop, horaires_list_dict=False, fusion_creneaux=True,
            view_mode='planning', return_fields=[]):
        """
        Fonction appelée par le javascript de la vue Planning.
        Renvoie toutes les informations nécessaires à l'affichage de la vue Planning:
        Les segments horaires, les infos de fillerbars, les infos de créneaux dispos
        :param employee_ids: [List] d'id des employés à évaluer
        :param date_start: [String] Date de début d'évaluation (incluse)
        :param date_stop: [String] Date de fin d'évaluation (incluse)
        :param horaires_list_dict: [Dict] segments des employés
        :param fusion_creneaux: True si on veut fusionner les créneaux libres qui se succèdent sans intervention
        :return: [Dict] de la forme {employee_id: {valeurs}, ..}
        """
        employee_obj = self.env['hr.employee']
        employees = employee_obj.browse(employee_ids)
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        intervention_obj = self.env['of.planning.intervention'].with_context(
            tz=self._context.get('tz'), virtual_id=True)
        tz = pytz.timezone(self._context['tz'])
        # avec les heures hiver/été, le tz_offset peut varier pour une même timezone, on prend donc la date de début
        # en tant que référence (c'est un lundi)
        tz_offset = tz.localize(fields.Datetime.from_string(date_start)).strftime('%z')

        # durée minimale pour qu'un créneau libre soit consiféré comme disponible
        duree_min = self.env['ir.values'].get_default("of.intervention.settings", "duree_min_creneaux_dispo") or 0.5

        jours_feries = self.env.user.company_id.get_jours_feries(date_start, date_stop)
        if view_mode == 'planning':
            passer_jours_feries = False
        else:
            passer_jours_feries = self.env['ir.values'].get_default('of.intervention.settings', 'ignorer_jours_feries')

        # On récupère les segments des employés s'ils ne sont pas fournis en paramètre
        if not horaires_list_dict:
            horaires_list_dict = employees.get_horaires(date_start, date_stop)

        # emp_info_force_min_date utilisé dans le fichier des tests
        date_today_str = self._context.get('emp_info_force_min_date', fields.Date.today())

        # Les Date et Datetime sont stockés en UTC, on les transforme en local
        date_current_naive_dt = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")  # datetime naif
        date_current_utc_dt = pytz.utc.localize(date_current_naive_dt, is_dst=None)  # datetime utc
        date_current_locale_dt = date_current_utc_dt.astimezone(tz)  # datetime local
        date_stop_naive_dt = datetime.strptime(date_stop, "%Y-%m-%d %H:%M:%S")  # datetime naif
        date_stop_utc_dt = pytz.utc.localize(date_stop_naive_dt, is_dst=None)  # datetime utc
        date_stop_locale_dt = date_stop_utc_dt.astimezone(tz)  # datetime local

        date_start_da = fields.Date.from_string(fields.Datetime.to_string(date_current_locale_dt)[:10])
        date_stop_da = fields.Date.from_string(fields.Datetime.to_string(date_stop_locale_dt)[:10])

        # Pré-remplissage du résultat
        res = {id_emp: {'segments': horaires_list_dict[id_emp], 'fillerbars': [], 'creneaux_dispo': []}
               for id_emp in employee_ids}

        un_jour = timedelta(days=1)

        # On récupère les interventions de tous les employés sur la période
        all_interventions = intervention_obj.sudo().search([
            ('employee_ids', 'in', employees.ids),
            ('date_prompt', '<=', fields.Date.to_string(date_stop_da)),
            ('date_deadline_prompt', '>=', fields.Date.to_string(date_start_da)),
            ('state', 'not in', ('cancel', 'postponed'))], order='date')

        if view_mode == 'planning':
            if 'id' not in return_fields:
                return_fields.append('id')
            res['interventions'] = [
                {
                    field: intervention_obj._fields[field].convert_to_read(interv[field], interv)
                    for field in return_fields
                }
                for interv in all_interventions
            ]
        for employee in employees:
            employee_id = employee.id
            res[employee_id]['tz'] = self._context.get('tz')
            res[employee_id]['tz_offset'] = tz_offset
            res[employee_id]['color_bg'] = employee.of_color_bg
            res[employee_id]['color_ft'] = employee.of_color_ft
            # liste d'index qui a une colonne associe un index de segment horaire
            # exemple: Une semaine à évaluer dont les 2 premiers jours sont sur un segment et le reste sur le suivant
            # res[employee_id]['col_offset_to_segment'] = [x, x, x+1, x+1, x+1, x+1, x+1]
            res[employee_id]['col_offset_to_segment'] = []
            segments_horaires = res[employee_id]['segments']
            index_courant = 0  # index du segment courant
            i_col_offset_to_segment = 0  # index qui à un col_offset associe un index de segment horaires
            segment_courant = segments_horaires and segments_horaires[index_courant] or False
            if not segment_courant:  # foolproofing
                continue
            fillerbarzz = []  # liste des fillerbars. Une par jour
            creneaux_dispozz = []  # liste de liste pour les créneaux dispos. Une sous-liste par jour
            date_current_da = date_start_da
            # Un premier filtered avant la boucle sur date, évite de générer le browse_record employee_ids pour chaque
            # date parcourue, gain de temps conséquent.
            employee_interventions = all_interventions.filtered(lambda i: employee_id in i.employee_ids.ids)

            # Parcours de toutes les dates à évaluer
            while date_current_da <= date_stop_da:
                date_current_str = fields.Date.to_string(date_current_da)
                res[employee_id]['col_offset_to_segment'].append(i_col_offset_to_segment)
                num_jour = date_current_da.isoweekday()
                # Pré-remplissage de la fillerbar
                fillerbar = {
                    'nb_heures_travaillees': 0.0,
                    'heures_travaillees_str': u"0h00",
                    'nb_heures_disponibles': 0.0,
                    'nb_heures_occupees': 0.0,
                    'heures_occupees_str': u"0h00",
                    'pct_disponible': 0.0,
                    'pct_occupe': 0.0,
                    'creneaux_du_jour': "",
                }

                # le jour est férié et la case "Ignorer jours fériés" est cochée
                if passer_jours_feries and date_current_str in jours_feries:
                    horaires_du_jour = []
                else:
                    horaires_du_jour = segment_courant[2].get(num_jour, False)  # [ [h_debut, h_fin] ,  .. ]
                if not horaires_du_jour:
                    # L'employé ne travaille pas ce jour-ci
                    fillerbarzz.append(fillerbar)
                    creneaux_dispozz.append([])
                    date_current_da += un_jour
                    date_current_str = fields.Date.to_string(date_current_da)
                    # segment_courant[1] == False quand segment sans date de fin
                    if segment_courant[1] and segment_courant[1] < date_current_str:
                        if len(segments_horaires) > index_courant + 1:  # changement de segment horaires courant
                            index_courant += 1
                            segment_courant = segments_horaires[index_courant]
                            i_col_offset_to_segment = index_courant
                    continue

                # String représentant les créneaux travaillés de la journée
                fillerbar['creneaux_du_jour'] = ", ".join(["-".join(hours_to_strs(creneau[0], creneau[1]))
                                                           for creneau in horaires_du_jour])
                fillerbar['nb_heures_travaillees'] = sum([round(c[1] - c[0], 5) for c in horaires_du_jour])
                fillerbar['heures_travaillees_str'] = hours_to_strs(fillerbar['nb_heures_travaillees'])
                journee_debut = horaires_du_jour[0][0]
                journee_fin = horaires_du_jour[-1][1]

                # On récupère tous les rdvs de la journée
                interventions = employee_interventions.filtered(
                    lambda i: i.date_prompt[:10] <= date_current_str <= i.date_deadline_prompt[:10])
                intervention_liste = []
                # Journée entièrement libre
                if not interventions:
                    fillerbar['nb_heures_disponibles'] = fillerbar['nb_heures_travaillees']
                    fillerbar['pct_disponible'] = 100.0
                    fillerbarzz.append(fillerbar)
                    # Ne pas calculer les créneaux dispos dans le passé
                    if date_current_str >= date_today_str:
                        creneaux_dispo = intervention_obj.get_creneaux_dispo(
                            employee_id, date_current_str, intervention_liste, horaires_du_jour, duree_min, False,
                            fusion_creneaux)
                    else:
                        creneaux_dispo = []
                    creneaux_dispozz.append(creneaux_dispo)
                    date_current_da += un_jour
                    date_current_str = fields.Date.to_string(date_current_da)
                    # segment_courant[1] == False quand segment sans date de fin
                    if segment_courant[1] and segment_courant[1] < date_current_str:
                        if len(segments_horaires) > index_courant + 1:  # changement de segment horaires
                            index_courant += 1
                            segment_courant = segments_horaires[index_courant]
                            i_col_offset_to_segment = index_courant
                    continue

                nb_heures_occupees = 0.0
                jour_deb_dt = tz.localize(datetime.strptime(date_current_str+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
                jour_fin_dt = tz.localize(datetime.strptime(date_current_str+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
                for interv in interventions:
                    intervention_heures = [interv]
                    # data = data_interventions_dict[intervention.id]
                    for intervention_heure in (interv.date_prompt, interv.date_deadline_prompt):
                        # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                        intervention_locale_dt = fields.Datetime.context_timestamp(
                            self, fields.Datetime.from_string(intervention_heure))

                        # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                        #   (pour les RDVs étalées sur plusieurs jours)
                        intervention_locale_dt = max(intervention_locale_dt, jour_deb_dt)
                        intervention_locale_dt = min(intervention_locale_dt, jour_fin_dt)
                        date_intervention_locale_flo = round(intervention_locale_dt.hour +
                                                             intervention_locale_dt.minute / 60.0 +
                                                             intervention_locale_dt.second / 3600.0, 5)
                        intervention_heures.append(date_intervention_locale_flo)
                    # remplacer minuit dans les heures de début et de fin par les heures de début et fin de journée
                    # pour les RDVs sur plusieurs jours
                    if intervention_heures[1] <= 0.25:
                        intervention_heures[1] = journee_debut
                    if intervention_heures[2] >= 23.75:
                        intervention_heures[2] = journee_fin
                    temps_pause = intervention_obj.pause_interv((intervention_heures[1], intervention_heures[2]),
                                                                horaires_du_jour)
                    nb_heures_occupees += round(intervention_heures[2] - intervention_heures[1] - temps_pause, 5)
                    intervention_liste.append(intervention_heures)
                # remplissage de la fillerbar du jour
                fillerbar['nb_heures_occupees'] = nb_heures_occupees
                fillerbar['heures_occupees_str'] = hours_to_strs(fillerbar['nb_heures_occupees'])
                fillerbar['pct_occupe'] = fillerbar['nb_heures_occupees'] * 100 / fillerbar['nb_heures_travaillees']
                fillerbar['nb_heures_disponibles'] = fillerbar['nb_heures_travaillees'] - nb_heures_occupees
                if fillerbar['nb_heures_disponibles'] <= 0.0:
                    fillerbar['nb_heures_disponibles'] = 0.0
                    fillerbar['pct_disponible'] = 0.0
                else:
                    fillerbar['pct_disponible'] = (fillerbar['nb_heures_disponibles']
                                                   * 100 / fillerbar['nb_heures_travaillees'])

                fillerbarzz.append(fillerbar)
                # Ne pas calculer les créneaux dispos dans le passé
                if date_current_str >= date_today_str:
                    intervention_forcee = any(i.forcer_dates for i in interventions)
                    creneaux_dispo = intervention_obj.get_creneaux_dispo(
                        employee_id, date_current_str, intervention_liste, horaires_du_jour, duree_min,
                        intervention_forcee, fusion_creneaux)
                else:
                    creneaux_dispo = []
                creneaux_dispozz.append(creneaux_dispo)

                date_current_da += un_jour
                date_current_str = fields.Date.to_string(date_current_da)
                # segment_courant[1] == False quand segment sans date de fin
                if segment_courant[1] and segment_courant[1] < date_current_str:
                    if len(segments_horaires) > index_courant + 1:
                        # changement de segment horaires
                        index_courant += 1
                        segment_courant = segments_horaires[index_courant]
                        i_col_offset_to_segment = index_courant
            res[employee_id]['fillerbars'] = fillerbarzz
            res[employee_id]['creneaux_dispo'] = creneaux_dispozz
        return res


class OFInterventionConfiguration(models.TransientModel):
    _inherit = 'of.intervention.settings'

    planningview_employee_exclu_ids = fields.Many2many(
        'hr.employee', string=u"(OF) Exculsion d'intervenants", help=u"Employés à NE PAS montrer en vue planning",
        domain=['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)])
    planningview_calendar = fields.Boolean(
        string=u"(OF) affichage", help=u"Cocher pour que les évènements soit disposés comme ceux de la vue calendrier.")
    planningview_h2px = fields.Integer(string=u"(OF) 1 heure = ")
    planningview_min_time = fields.Integer(string='(OF) Heure min', help=u"Heure minimale affichée")
    planningview_max_time = fields.Integer(string='(OF) Heure max', help=u"Heure maximale affichée")
    planningview_time_line = fields.Char(
        string="(OF) lignes d'heures", help=u"Entrez les heures sous forme d'entiers séparées par des virgules")

    @api.onchange('planningview_calendar')
    def _onchange_planningview_calendar(self):
        if self.planningview_calendar:
            if not self.planningview_h2px:
                self.planningview_h2px = 30
            if not self.planningview_min_time:
                self.planningview_min_time = 7
            if not self.planningview_max_time:
                self.planningview_max_time = 20
            if not self.planningview_time_line:
                self.planningview_time_line = "12"

    @api.multi
    def set_planningview_employee_exclu_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings',
            'planningview_employee_exclu_ids',
            [(6, 0, self.planningview_employee_exclu_ids.ids)],
        )

    @api.multi
    def set_planningview_calendar_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings',
            'planningview_calendar',
            self.planningview_calendar,
        )

    @api.multi
    def set_planningview_h2px_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings',
            'planningview_h2px',
            self.planningview_h2px,
        )

    @api.multi
    def set_planningview_min_time_defaults(self):
        if not 0 <= self.planningview_min_time < 24:
            raise ValidationError(u"l'heure minimale doit être entre 0 et 24! (et idéalement pas 24...)")
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'planningview_min_time', self.planningview_min_time)

    @api.multi
    def set_planningview_max_time_defaults(self):
        if not 0 <= self.planningview_max_time <= 24:
            raise ValidationError(u"l'heure maximale doit être entre 0 et 24! (et idéalement pas 0...)")
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'planningview_max_time', self.planningview_max_time)

    @api.multi
    def set_planningview_time_line_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'planningview_time_line', self.planningview_time_line)


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[PLANNING_VIEW])

    @api.model
    def postprocess(self, model, node, view_id, in_tree_view, model_fields):
        """Rajout des champs par défaut à la fields_view"""
        fields = super(IrUIView, self).postprocess(model, node, view_id, in_tree_view, model_fields)
        if node.tag == 'planning':
            modifiers = {}
            # Tous ces champs peuvent être définis comme attributs de la balise <planning>
            # et n'ont pas besoin d'être rajoutés dans l'architecture de la vue
            for additional_field in ('date_start', 'date_delay', 'date_stop', 'all_day', 'resource',
                                     'color_bg', 'color_ft'):
                if node.get(additional_field):
                    fields[node.get(additional_field)] = {}

            if not self._apply_group(model, node, modifiers, fields):
                # node must be removed, no need to proceed further with its children
                return fields

            # The view architeture overrides the python model.
            # Get the attrs before they are (possibly) deleted by check_group below
            orm.transfer_node_to_modifiers(node, modifiers, self._context, in_tree_view)

            for f in node:
                # useless here? if children or (node.tag == 'field' and f.tag in ('filter', 'separator')):
                fields.update(self.postprocess(model, f, view_id, in_tree_view, model_fields))

            orm.transfer_modifiers_to_node(modifiers, node)
        return fields


class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[PLANNING_VIEW])
