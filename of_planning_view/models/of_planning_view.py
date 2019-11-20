# -*- coding: utf-8 -*-

from odoo.osv import orm
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from odoo import models, fields, api
import json
from odoo.addons.of_planning_tournee.wizard.rdv import hours_to_strs
from odoo.addons.of_utils.models.of_utils import se_chevauchent

import pytz
from datetime import datetime, timedelta

PLANNING_VIEW = ('planning', 'Planning')

@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class HREmployee(models.Model):
    _inherit = "hr.employee"

    planning_seq = fields.Integer(string=u"Séquence affichage vue Planning", default=20)


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
            'name': self.name,
            }
        return res

class OfPlanifTag(models.Model):
    _name = 'of.planif.tag'
    _description = u"Étiquettes de propositions d'interventions"

    name = fields.Char(string='Nom', required=True, translate=True)
    color = fields.Integer(string='Index couleur')
    active = fields.Boolean(default=True, help=u"Le champ 'Active' vous permet de cacher l'étiquette sans la supprimer.")


class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _inherit = ["of.planning.intervention", "of.readgroup", "of.calendar.mixin"]

    @api.model
    def get_creneaux_dispo(self, employee_id, date, intervention_heures, creneaux_travailles,
                               duree_min, intervention_forcee):  # interventions et creneaux sont des listes de tuples (heure_debut, heure_fin)
        """Similaire au calcul de créneaux dispo de rdv.py.
        L'idée ici est de fusionner les créneaux dispos consécutifs.
        exple: une journée sans intervention programmée ne doit avoir qu'un créneau dispo"""
        compare_precision = 5
        #index_courant = intervention_heures and 0 or -1  # index de parcours de intervention_heures
        employee = self.env['hr.employee'].browse(int(employee_id))
        #deb = creneaux_travailles[index_courant][0]  # début courant
        #fin = creneaux_travailles[index_courant][1]  # fin courante
        creneaux = []
        vals = {}
        #warning_forcer_horaires = any([forcee for forcee ])
        lieu_depart = employee.of_address_depart_id and employee.of_address_depart_id.get_infos_lieu() or False
        lieu_retour = employee.of_address_retour_id and employee.of_address_retour_id.get_infos_lieu() or False
        tournee = self.env['of.planning.tournee'].search([('date', '=', date), ('employee_id', '=', employee_id)], limit=1)
        if tournee:
            secteur = tournee.secteur_id
            # les lieux de départ et de retour d'une tournée priment sur ceux de l'employé
            lieu_depart = tournee.address_depart_id and tournee.address_depart_id.get_infos_lieu() or lieu_depart
            lieu_retour = tournee.address_retour_id and tournee.address_retour_id.get_infos_lieu() or lieu_retour
        else:
            secteur = False

        if not creneaux_travailles:
            return []
        if not intervention_heures:
            secteur_str = secteur and secteur.name or ""
            vals['heure_debut'] = creneaux_travailles[0][0]
            vals['heure_fin'] = creneaux_travailles[-1][-1]
            vals['lieu_debut'] = lieu_depart
            vals['lieu_fin'] = lieu_retour
            vals['duree'] = sum([c[1] - c[0] for c in creneaux_travailles])
            vals['creneaux_reels'] = creneaux_travailles
            vals['secteur_id'] = secteur and secteur.id or False
            vals['secteur_str'] = secteur_str
            vals['display_secteur'] = True
            vals['warning_horaires'] = intervention_forcee
            return vals['duree'] >= duree_min and [vals] or []

        deb_h = creneaux_travailles[0][0]
        fin_h = creneaux_travailles[0][1]
        avant_listzz = filter(lambda t: t[1] < deb_h, intervention_heures)  # toutes les intervention qui commencent avant le premier creneau de la journée
        pendant_listzz = []  # sera rempli dans le for
        apres_listzz = [tup for tup in intervention_heures if tup not in avant_listzz]
        lieu_deb = avant_listzz and avant_listzz[-1][0].address_id and avant_listzz[-1][0].address_id.get_infos_lieu() or lieu_depart
        secteur = avant_listzz and avant_listzz[-1][0].secteur_id or secteur
        secteur_str = secteur and secteur.name or ""
        fin_libre = False

        for index_creneau in range(len(creneaux_travailles)):
            creneau = creneaux_travailles[index_creneau]
            pendant_listzz = filter(lambda t: t[1] < creneau[1], apres_listzz)
            if avant_listzz and avant_listzz[-1][2] > creneau[0]:  # chevauchement
                pendant_listzz.insert(0, avant_listzz.pop(-1))
            apres_listzz = filter(lambda t: t not in pendant_listzz, apres_listzz)
            already_added = False
            if fin_libre:  # fusion ou nettoyage
                fin = pendant_listzz and pendant_listzz[0][1] or creneau[1]
                vals = creneaux[-1]
                vals['heure_fin'] = fin
                vals['duree'] += fin - creneau[0]
                vals['lieu_fin'] = lieu_fin
                vals['creneaux_reels'] += [(creneau[0], fin)]
                if creneaux[-1]["duree"] < duree_min:
                    creneaux.pop(-1)
                already_added = True
                vals = {}
            elif creneaux and creneaux[-1]["duree"] < duree_min:
                creneaux.pop(-1)

            while pendant_listzz:
                interv_list = pendant_listzz.pop(0)  # (intervention, heure_debut, heure_fin)
                lieu_fin = interv_list[0].address_id and interv_list[0].address_id.get_infos_lieu() or False

                if not already_added and float_compare(interv_list[1] - creneau[0], duree_min, compare_precision) >= 0:
                    # l'intervention commence après le début du créneau
                    # on ajoute le créneau dispo à la liste
                    vals['heure_debut'] = creneau[0]
                    vals['heure_fin'] = interv_list[1]
                    vals['lieu_debut'] = lieu_deb
                    vals['lieu_fin'] = lieu_fin
                    vals['duree'] = interv_list[1] - creneau[0]
                    vals['creneaux_reels'] = [(creneau[0], interv_list[1])]
                    vals['secteur_id'] = secteur and secteur.id or False
                    vals['secteur_str'] = secteur_str
                    vals['display_secteur'] = False
                    vals['warning_horaires'] = intervention_forcee
                    creneaux.append(vals)
                    vals = {}
                elif already_added:
                    already_added = False
                # mettre à jour les données pour la prochaine itération interventions
                secteur = interv_list[0].secteur_id or secteur
                secteur_str = secteur and secteur.name or ""
                creneau[0] = interv_list[2]  # min(creneau[1], interv_list[2])?
                avant_listzz.append(interv_list)
                lieu_deb = lieu_fin
            if not already_added and float_compare(creneau[1], creneau[0], compare_precision) > 0:
                # il reste du temps entre la fin de la dernière intervention de pendant_listzz et la fin du créneau
                # on ajoute le créneau dispo à la liste:
                #   si la durée est suffisante dans le cas du dernier créneau de la journée
                #   tout le temp sinon: il sera fusionné ou supprimé dans la prochaine itération créneau
                lieu_fin = apres_listzz and apres_listzz[0][0].address_id and apres_listzz[0][0].address_id.get_infos_lieu() or False
                vals['heure_debut'] = creneau[0]
                vals['heure_fin'] = creneau[1]
                vals['lieu_debut'] = lieu_deb
                vals['lieu_fin'] = lieu_fin
                vals['duree'] = creneau[1] - creneau[0]
                vals['creneaux_reels'] = [(creneau[0], creneau[1])]
                vals['secteur_id'] = secteur and secteur.id or False
                vals['secteur_str'] = secteur_str
                vals['display_secteur'] = False
                vals['warning_horaires'] = intervention_forcee
                if float_compare(vals['duree'], duree_min, compare_precision) >= 0 or index_creneau != len(creneaux_travailles) -1:
                    # ne pas ajouter le dernier créneau de la journée si il est trop court car il ne sera pas nettoyé
                    vals['lieu_fin'] = apres_listzz and apres_listzz[0][0].address_id and \
                        apres_listzz[0][0].address_id.get_infos_lieu() or lieu_retour
                    creneaux.append(vals)
                    fin_libre = True
                vals = {}

            elif not already_added:
                fin_libre = False
            # mettre à jour les données pour la prochaine itération créneaux
            lieu_deb = lieu_fin

        return creneaux

    @api.model
    def get_creneaux_dispo_old(self, employee_id, date, intervention_heures, creneaux_travailles, duree_min=1.0):  # interventions et creneaux sont des listes de tuples (heure_debut, heure_fin)
        """Similaire au calcul de créneaux dispo de rdv.py.
        L'idée ici est de fusionner les créneaux dispos consécutifs.
        exple: une journée sans intervention programmée ne doit avoir qu'un créneau dispo"""
        index_courant = 0
        employee = self.env['hr.employee'].browse(int(employee_id))
        deb = creneaux_travailles[index_courant][0]  # début courant
        fin = creneaux_travailles[index_courant][1]  # fin courante
        creneaux = []
        vals={}
        to_add = False
        lieu_depart = employee.of_address_depart_id and employee.of_address_depart_id.get_infos_lieu() or False
        lieu_retour = employee.of_address_retour_id and employee.of_address_retour_id.get_infos_lieu() or False
        tournee = self.env['of.planning.tournee'].search([('date', '=', date), ('employee_id', '=', employee_id)], limit=1)
        if tournee:
            secteur = tournee.secteur_id
            # les lieux de départ et de retour d'une tournée priment sur ceux de l'employé
            lieu_depart = tournee.address_depart_id and tournee.address_depart_id.get_infos_lieu() or lieu_depart
            lieu_retour = tournee.address_retour_id and tournee.address_retour_id.get_infos_lieu() or lieu_retour
        else:
            secteur = False
        lieu_deb = lieu_depart
        for intervention, intervention_deb, intervention_fin in intervention_heures + [(False, 24, 24)]:
            secteur = intervention and intervention.secteur_id or secteur
            secteur_str = secteur and secteur.name or ""
            if not intervention:  # plus d'interventions, reste-t-il de la place avant la fin de la journée?
                if deb and deb < fin:  # de la place sur ce créneau horaire
                    vals['heure_debut'] = deb
                    vals['heure_fin'] = fin
                    vals['lieu_debut'] = lieu_deb
                    vals['lieu_fin'] = lieu_retour
                    vals['duree'] = fin - deb
                    vals['creneaux_reels'] = [(deb, fin)]
                    to_add = True
                while len(creneaux_travailles) > index_courant + 1:  # rajouter le reste des créneaux s'il y en a
                    index_courant += 1
                    deb = creneaux_travailles[index_courant][0]  # début courant
                    fin = creneaux_travailles[index_courant][1]  # fin courante
                    vals['heure_fin'] = fin
                    vals['duree'] += fin - deb
                    vals['creneaux_reels'].append((deb, fin))
                if to_add and vals['duree'] >= duree_min:
                    vals['secteur_id'] = secteur and secteur.id or False
                    vals['secteur_str'] = secteur_str
                    vals['interv_suiv_id'] = False
                    vals['display_secteur'] = not intervention_heures  # on affiche le secteur seulement si il n'y a pas d'interventions dans la journée
                    creneaux.append(vals)
                break
            elif deb and deb < intervention_deb:  # du temps avant le début de l'intervention
                if fin < intervention_deb:  # l'intervention commence sur un autre creneau: préparation du créneau dispo
                    vals['heure_debut'] = deb
                    vals['heure_fin'] = fin
                    vals['duree'] = fin - deb
                    vals['creneaux_reels'] = [(deb, fin)]
                    index_courant += 1
                    deb = creneaux_travailles[index_courant][0]  # début courant
                    fin = creneaux_travailles[index_courant][1]  # fin courante
                    while fin < intervention_deb:  # parcourir les créneaux jusqu'à arriver au créneau de l'intervention
                        vals['heure_fin'] = fin
                        vals['duree'] += fin - deb
                        vals['creneaux_reels'].append((deb, fin))
                        index_courant += 1
                        deb = creneaux_travailles[index_courant][0]  # début courant
                        fin = creneaux_travailles[index_courant][1]  # fin courante
                    # si l'intervention commence sur le début d'un créneau: la fin du créneau dispo est la fin du créneau précédent
                    # => l'heure de fin du créneau dispo est déjà bonne
                    # si l'intervention NE commence PAS sur le début d'un créneau: la fin du créneau dispo est le début de l'intervention
                    if deb < intervention_deb:
                        vals['heure_fin'] = intervention_deb
                else:  # l'intervention commence sur ce même créneau
                    vals['heure_debut'] = deb
                    vals['duree'] = 0
                    vals['creneaux_reels'] = []
                    vals['heure_fin'] = intervention_deb
                vals['lieu_debut'] = lieu_deb
                vals['lieu_fin'] = intervention.address_id and intervention.address_id.get_infos_lieu() or False
                vals['duree'] += intervention_deb - deb
                vals['creneaux_reels'].append((deb, intervention_deb))
                if vals['duree'] >= duree_min:  # un créneau à ajouter
                    vals['secteur_id'] = secteur and secteur.id or False
                    vals['secteur_str'] = secteur_str
                    vals['interv_suiv_id'] = intervention.id
                    creneaux.append(vals)
                vals = {}
                if intervention_fin < fin:  # l'intervention se fini avant la fin du créneau horaire
                    deb = intervention_fin  # le nouveau début potentiel sur ce même créneau est la fin de l'intervention
                else:  # l'intervention termine après la fin du créneau horaire
                    index_courant += 1
                    if len(creneaux_travailles) > index_courant:  # Nouveau créneau à parcourir
                        deb = creneaux_travailles[index_courant][0]  # début courant
                        deb = max(deb, intervention_fin)
                        fin = creneaux_travailles[index_courant][1]  # fin courante
                        while deb and deb >= fin:  # repositionner le début sur un créneau si besoin
                            index_courant += 1
                            if len(creneaux_travailles) > index_courant:
                                fin = creneaux_travailles[index_courant][1]
                            else:
                                deb = False
                    else:
                        deb = False
                # le nouveau lieu de départ est le lieu de l'ntervention courante
                lieu_deb = intervention.address_id and intervention.address_id.get_infos_lieu() or False
            elif deb and deb < intervention_fin:  # si la journée commence par une intervention
                deb = intervention_fin
                # le nouveau lieu de départ est le lieu de l'ntervention courante
                lieu_deb = intervention.address_id and intervention.address_id.get_infos_lieu() or False
                while deb and deb >= fin:  # repositionner le début sur un créneau si besoin
                    index_courant += 1
                    if len(creneaux_travailles) > index_courant:
                        fin = creneaux_travailles[index_courant][1]
                    else:
                        deb = False
            # mettre à jour l'intervention précédente
            vals['interv_prec_id'] = intervention.id

        return creneaux

    @api.model
    def pause_interv(self, heures_interv, creneaux):
        """Renvois la durée de pause entre le début et la fin d'une intervention"""
        heure_debut = heures_interv[0]
        heure_fin = heures_interv[1]
        index_debut = 0
        index_fin = len(creneaux) - 1
        temps_chevauche = 0.0
        for i in range(len(creneaux)):
            creneau_courant = creneaux[i]
            if creneau_courant[0] <= heure_debut and heure_debut <= creneau_courant[1]:
                index_debut = i
                break
        for i in range(index_debut, len(creneaux)):
            creneau_courant = creneaux[i]
            if creneau_courant[0] <= heure_fin and heure_fin <= creneau_courant[1]:
                index_fin = i
                break
        while index_debut < index_fin:
            temps_chevauche += (creneaux[index_debut + 1][0] - creneaux[index_debut][1])
            index_debut += 1
        return temps_chevauche

    @api.model
    def get_emp_horaires_info(self, employee_ids, date_start, date_stop, horaires_list_dict=False):
        intervention_obj = self.env['of.planning.intervention']
        employee_obj = self.env['hr.employee']
        employees = employee_obj.browse(employee_ids)
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        compare_precision = 5

        duree_min = self.env['ir.values'].get_default("of.intervention.settings", "duree_min_creneaux_dispo") or 1

        if not horaires_list_dict:
            horaires_list_dict = employees.get_horaires_list_dict(date_start, date_stop)

        date_today_str = fields.Date.today()

        date_current_naive_dt = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")  # datetime naif
        date_current_utc_dt = pytz.utc.localize(date_current_naive_dt, is_dst=None)  # datetime utc
        date_current_locale_dt = date_current_utc_dt.astimezone(tz)  # datetime local
        date_stop_naive_dt = datetime.strptime(date_stop, "%Y-%m-%d %H:%M:%S")  # datetime naif
        date_stop_utc_dt = pytz.utc.localize(date_stop_naive_dt, is_dst=None)  # datetime utc
        date_stop_locale_dt = date_stop_utc_dt.astimezone(tz)  # datetime local

        date_start_da = fields.Date.from_string(fields.Datetime.to_string(date_current_locale_dt)[:10])
        date_current_da = fields.Date.from_string(fields.Datetime.to_string(date_current_locale_dt)[:10])
        date_stop_da = fields.Date.from_string(fields.Datetime.to_string(date_stop_locale_dt)[:10])

        res = {id_emp: {'segments': horaires_list_dict[id_emp], 'fillerbars': [], 'creneaux_dispo': []} for id_emp in employee_ids}

        un_jour = timedelta(days=1)

        is_jour_temp = False
#float_compare(la_duree_restante, 0.0, compare_precision)  > 0.0
        for employee in employees:
            employee_id = employee.id
            res[employee_id]['color_bg'] = employee.of_color_bg
            res[employee_id]['color_ft'] = employee.of_color_ft
            res[employee_id]['col_offset_to_segment'] = []
            segments_horaires = res[employee_id]['segments']
            index_courant = 0
            i_col_offset_to_segment = 0  # indexe qui à un col_offset associe un indexe de segment horaires
            segment_courant = segments_horaires and segments_horaires[index_courant] or False
            if not segment_courant:  # foolproofing
                continue
            fillerbarzz = []
            creneaux_dispozz = []
            date_current_da = date_start_da

            while date_current_da <= date_stop_da:
                res[employee_id]['col_offset_to_segment'].append(i_col_offset_to_segment)
                num_jour = date_current_da.isoweekday()

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

                horaires_du_jour = segment_courant[2].get(num_jour, False)  # [ (h_debut, h_fin) ,  .. ]
                if not horaires_du_jour:
                    fillerbarzz.append(fillerbar)
                    creneaux_dispozz.append([])
                    date_current_da += un_jour
                    date_current_str = fields.Date.to_string(date_current_da)
                    if segment_courant[1] and segment_courant[1] < date_current_str:  # segment_courant[1] == False quand segment sans date de fin
                        if len(segments_horaires) > index_courant + 1:  # changement de segment horaires
                            index_courant += 1
                            segment_courant = segments_horaires[index_courant]
                            i_col_offset_to_segment = index_courant
                    continue

                fillerbar['creneaux_du_jour'] = ["-".join(hours_to_strs(creneau[0], creneau[1])) for creneau in horaires_du_jour]
                fillerbar['creneaux_du_jour'] = ", ".join(fillerbar['creneaux_du_jour'])
                fillerbar['nb_heures_travaillees'] = sum([round(c[1] - c[0], 5) for c in horaires_du_jour])
                fillerbar['heures_travaillees_str'] = hours_to_strs(fillerbar['nb_heures_travaillees'])
                journee_debut = horaires_du_jour[0][0]
                journee_fin = horaires_du_jour[-1][1]

                date_current_str = fields.Date.to_string(date_current_da)
                interventions = intervention_obj.sudo().search([('employee_ids', 'in', employee_id),
                                                         ('date', '<=', date_current_str),
                                                         ('date_deadline', '>=', date_current_str),
                                                         ('state', 'in', ('draft', 'confirm', 'done')),
                                                         ], order='date')
                intervention_liste = []
                if not interventions:
                    fillerbar['nb_heures_disponibles'] = fillerbar['nb_heures_travaillees']
                    fillerbar['pct_disponible'] = 100.0
                    fillerbarzz.append(fillerbar)
                    if date_current_str >= date_today_str:
                        creneaux_dispo = intervention_obj.get_creneaux_dispo(employee_id, date_current_str, intervention_liste,
                                                                         horaires_du_jour, duree_min, False)
                    else:
                        creneaux_dispo = []
                    creneaux_dispozz.append(creneaux_dispo)
                    date_current_da += un_jour
                    date_current_str = fields.Date.to_string(date_current_da)
                    if segment_courant[1] and segment_courant[1] < date_current_str:  # segment_courant[1] == False quand segment sans date de fin
                        if len(segments_horaires) > index_courant + 1:  # changement de segment horaires
                            index_courant += 1
                            segment_courant = segments_horaires[index_courant]
                            i_col_offset_to_segment = index_courant
                    continue

                nb_heures_occupees = 0.0
                jour_deb_dt = tz.localize(datetime.strptime(date_current_str+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
                jour_fin_dt = tz.localize(datetime.strptime(date_current_str+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
                for intervention in interventions:
                    intervention_heures = [intervention]
                    for intervention_heure in (intervention.date, intervention.date_deadline):
                        # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                        intervention_locale_dt = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention_heure))

                        # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                        #   (pour les interventions étalées sur plusieurs jours)
                        intervention_locale_dt = max(intervention_locale_dt, jour_deb_dt)
                        intervention_locale_dt = min(intervention_locale_dt, jour_fin_dt)
                        date_intervention_locale_flo = round(intervention_locale_dt.hour +
                                                          intervention_locale_dt.minute / 60.0 +
                                                          intervention_locale_dt.second / 3600.0, 5)
                        intervention_heures.append(date_intervention_locale_flo)
                    if intervention_heures[1] <= 0.25:
                        intervention_heures[1] = journee_debut
                    if intervention_heures[2] >= 23.75:
                        intervention_heures[2] = journee_fin
                    chevauchement = intervention_obj.pause_interv((intervention_heures[1], intervention_heures[2]), horaires_du_jour)
                    nb_heures_occupees += round(intervention_heures[2] - intervention_heures[1] - chevauchement, 5)
                    intervention_liste.append(intervention_heures)

                fillerbar['nb_heures_occupees'] = nb_heures_occupees
                fillerbar['heures_occupees_str'] = hours_to_strs(fillerbar['nb_heures_occupees'])
                fillerbar['pct_occupe'] = fillerbar['nb_heures_occupees'] * 100 / fillerbar['nb_heures_travaillees']
                fillerbar['nb_heures_disponibles'] = fillerbar['nb_heures_travaillees'] - nb_heures_occupees
                if fillerbar['nb_heures_disponibles'] <= 0.0:
                    fillerbar['nb_heures_disponibles'] = 0.0
                    fillerbar['pct_disponible'] = 0.0
                else:
                    fillerbar['pct_disponible'] = fillerbar['nb_heures_disponibles'] * 100 / fillerbar['nb_heures_travaillees']

                fillerbarzz.append(fillerbar)
                intervention_forcee = len(interventions.filtered(lambda i: i.forcer_dates)) > 0
                if date_current_str >= date_today_str:
                    creneaux_dispo = intervention_obj.get_creneaux_dispo(employee_id, date_current_str,
                                                                         intervention_liste,
                                                                         horaires_du_jour, duree_min, intervention_forcee)
                else:
                    creneaux_dispo = []
                creneaux_dispozz.append(creneaux_dispo)

                date_current_da += un_jour
                date_current_str = fields.Date.to_string(date_current_da)
                if segment_courant[1] and segment_courant[1] < date_current_str:  # segment_courant[1] == False quand segment sans date de fin
                    if len(segments_horaires) > index_courant + 1:  # changement de segment horaires
                        index_courant += 1
                        segment_courant = segments_horaires[index_courant]
                        i_col_offset_to_segment = index_courant
            res[employee_id]['fillerbars'] = fillerbarzz
            res[employee_id]['creneaux_dispo'] = creneaux_dispozz
        return res


class OFInterventionConfiguration(models.TransientModel):
    _inherit = 'of.intervention.settings'

    planningview_employee_exclu_ids = fields.Many2many('hr.employee', string=u"(OF) Exculsion d'intervenants",
                                                       help=u"Intervenants à NE PAS montrer en vue planning",
                                                       domain=[('of_est_intervenant', '=', True)])

    #planningview_employee_ids = fields.Many2many()

    """planningview_range_start = fields.Date(string=u"Date début vue planning",
                                           help=u"pris en compte en sous-marin pour conserver l'état de la vue planning"
                                                u"à niveau utilisateur")

    planningview_domain = fields.Char(string=u"Domaine vue planning",
                                      help=u"pris en compte en sous-marin pour conserver l'état de la vue planning"
                                           u"à niveau utilisateur")
    planningview_context = fields.Char(string=u"Contexte vue planning",
                                       help=u"pris en compte en sous-marin pour conserver l'état de la vue planning"
                                            u"à niveau utilisateur")"""

    planningview_filter_client = fields.Boolean(
        string=u"(OF) Nom du client", required=True, default=True,
        help=u"Afficher le nom du client des interventions en vue planning ?")

    planningview_filter_tache = fields.Boolean(
        string=u"(OF) Nom de la tâche", required=True, default=True,
        help=u"Afficher le nom de la tâche des interventions en vue planning ?")

    planningview_filter_zip = fields.Boolean(
        string=u"(OF) Code postal", required=True, default=True,
        help=u"Afficher le code postal des interventions en vue planning ?")

    planningview_filter_city = fields.Boolean(
        string=u"(OF) Ville", required=True, default=True,
        help=u"Afficher la ville des interventions en vue planning ?")

    planningview_filter_heure_debut = fields.Boolean(
        string=u"(OF) Heure de début", required=True, default=True,
        help=u"Afficher l'heure de début des interventions en vue planning ?")

    planningview_filter_heure_fin = fields.Boolean(
        string=u"(OF) Heure de fin", required=True, default=True,
        help=u"Afficher l'heure de fin des interventions en vue planning ?")

    planningview_filter_duree = fields.Boolean(
        string=u"(OF) Durée", required=True, default=True,
        help=u"Afficher la durée des interventions en vue planning ?")

    """@api.model
    def get_default_planningview_domain(self, fields):
        value = self.env['ir.values'].sudo().get_default('of.intervention.settings', 'planningview_domain', False)
        return {
            'planningview_domain': json.loads(value)
        }

    @api.model
    def get_default_planningview_context(self, fields):
        value = self.env['ir.values'].sudo().get_default('of.intervention.settings', 'planningview_context', False)
        return {
            'planningview_context': json.loads(value)
        }

    @api.model
    def get_default_planningview_context(self, fields):
        value = self.env['ir.values'].sudo().get_default('of.intervention.settings', 'planningview_context', False)
        return {
            'planningview_context': json.loads(value)
        }"""

    @api.multi
    def set_planningview_employee_exclu_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings',
            'planningview_employee_exclu_ids',
            [(6, 0, self.planningview_employee_exclu_ids.ids)],
        )

    """@api.multi
    def set_planningview_context_defaults(self):
        if not isinstance(self.planningview_context, basestring):
            self.planningview_context = json.dumps(self.planningview_context)
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_context', self.planningview_context)

    @api.multi
    def set_planningview_domain_defaults(self):
        if not isinstance(self.planningview_domain, basestring):
            self.planningview_domain = json.dumps(self.planningview_domain)
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_domain', self.planningview_domain)

    @api.multi
    def set_planningview_range_start_defaults(self):
        planningview_range_start_da = fields.Date.from_string(self.planningview_range_start)
        if planningview_range_start_da.weekday() != 0:  # n'est pas un lundi
            planningview_range_start_da -= timedelta(days=planningview_range_start_da.weekday() % 7)  # replacé un lundi
            self.planningview_range_start = fields.Date.to_string(planningview_range_start_da)
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_range_start', self.planningview_range_start)"""

    @api.multi
    def set_planningview_filter_client_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_filter_client', self.planningview_filter_client)

    @api.multi
    def set_planningview_filter_tache_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_filter_tache', self.planningview_filter_tache)

    @api.multi
    def set_planningview_filter_zip_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_filter_zip', self.planningview_filter_zip)

    @api.multi
    def set_planningview_filter_city_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_filter_city', self.planningview_filter_city)

    @api.multi
    def set_planningview_filter_heure_debut_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_filter_heure_debut', self.planningview_filter_heure_debut)

    @api.multi
    def set_planningview_filter_heure_fin_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_filter_heure_fin', self.planningview_filter_heure_fin)

    @api.multi
    def set_planningview_filter_duree_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.settings', 'planningview_filter_duree', self.planningview_filter_duree)

class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[PLANNING_VIEW])

    @api.model
    def postprocess(self, model, node, view_id, in_tree_view, model_fields):
        """Rajout des champs par défaut à la fields_view"""
        fields = super(IrUIView, self).postprocess(model, node, view_id, in_tree_view, model_fields)
        if node.tag == 'planning':
            modifiers = {}
            #@todo: décider les champs de base
            for additional_field in ('date_start', 'date_delay', 'date_stop', 'all_day', 'resource', 'color_bg', 'color_ft'):
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
