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
                           duree_min, intervention_forcee):
        """Similaire au calcul de créneaux dispo de rdv.py.
        L'idée ici est de fusionner les créneaux dispos consécutifs.
        exple: une journée sans intervention programmée ne doit avoir qu'un créneau dispo
        :type intervention_heures: listes de tuples (intervention, heure_debut, heure_fin)
        :type creneaux_travailles: listes de tuples (heure_debut, heure_fin)
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
                if creneaux_reels:
                    creneaux.append({
                        'heure_debut': heure_debut,
                        'heure_fin': creneaux_reels[-1][1],
                        'lieu_debut': lieu_depart,
                        'lieu_fin': lieu_fin,
                        'duree': sum(hor[1] - hor[0] for hor in creneaux_reels),
                        'creneaux_reels': creneaux_reels,
                        'secteur_id': secteur and secteur.id or False,
                        'secteur_str': secteur_str,
                        'display_secteur': display_secteur,
                        'warning_horaires': intervention_forcee,
                    })
                break

            heure_debut = interv_fin
            lieu_depart = lieu_fin
            if interv and not tournee:
                secteur = interv.secteur_id or secteur
                secteur_str = secteur and secteur.name or ""

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
        tz_offset = datetime.now(tz).strftime('%z')
        compare_precision = 5

        duree_min = self.env['ir.values'].get_default("of.intervention.settings", "duree_min_creneaux_dispo") or 1

        if not horaires_list_dict:
            horaires_list_dict = employees.get_horaires_list_dict(date_start, date_stop)

        date_today_str = self._context.get('emp_info_force_min_date', fields.Date.today())

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
            res[employee_id]['tz'] = self._context.get('tz')
            res[employee_id]['tz_offset'] = tz_offset
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

                horaires_du_jour = segment_courant[2].get(num_jour, False)  # [ [h_debut, h_fin] ,  .. ]
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
                        creneaux_dispo = intervention_obj.get_creneaux_dispo(employee_id, date_current_str,
                                                                             intervention_liste, horaires_du_jour,
                                                                             duree_min, False)
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

    @api.multi
    def set_planningview_employee_exclu_ids_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings',
            'planningview_employee_exclu_ids',
            [(6, 0, self.planningview_employee_exclu_ids.ids)],
        )

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
