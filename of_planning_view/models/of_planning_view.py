# -*- coding: utf-8 -*-

from odoo.osv import orm
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from odoo import models, fields, api

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

class OfPlanningIntervention(models.Model):
    _name = "of.planning.intervention"
    _inherit = ["of.planning.intervention", "of.readgroup", "of.calendar.mixin"]

    @api.model
    def get_fillerbar_data(self, equipe_id, date_start, date_stop):
        intervention_obj = self.env['of.planning.intervention']
        equipe = self.env['of.planning.equipe'].browse(int(equipe_id))
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        compare_precision = 5

        def get_creneaux_dispo(interventions_dates, creneaux_travailles, duree_min=1.0):  # interventions et creneaux sont des listes de tuples (heure_debut, heure_fin)
            """Similaire au calcul de créneaux dispo de rdv.py.
            L'idée ici est de fusionner les créneaux dispos consécutifs.
            exple: une journée sans intervention programmée ne doit avoir qu'un créneau dispo"""
            #@todo: debug lieu_deb
            index_courant = 0
            equipe = self.env['of.planning.equipe'].browse(int(equipe_id))
            deb = creneaux_travailles[index_courant][0]  # début courant
            fin = creneaux_travailles[index_courant][1]  # fin courante
            creneaux = []
            to_append = []
            vals={}
            lieu_depart = equipe.address_id and equipe.address_id.get_infos_lieu() or False
            lieu_retour = equipe.address_retour_id and equipe.address_retour_id.get_infos_lieu() or False
            lieu_deb = lieu_depart
            for intervention, intervention_deb, intervention_fin in interventions_dates + [(False, 24, 24)]:
                if not intervention:  # plus d'interventions, reste-t-il de la place avant la fin de la journée?
                    if deb and deb < fin:  # de la place sur ce créneau horaire
                        vals['heure_debut'] = deb
                        vals['heure_fin'] = fin
                        vals['lieu_debut'] = lieu_deb
                        vals['lieu_fin'] = lieu_retour
                        vals['duree'] = fin - deb
                    while len(creneaux_travailles) > index_courant + 1:  # rajouter le reste des créneaux s'il y en a
                        index_courant += 1
                        deb = creneaux_travailles[index_courant][0]  # début courant
                        fin = creneaux_travailles[index_courant][1]  # fin courante
                        vals['heure_fin'] = fin
                        vals['duree'] += fin - deb
                    if vals != {} and vals['duree'] >= duree_min:
                        creneaux.append(vals)
                elif deb and deb < intervention_deb:  # du temps avant le début de l'intervention
                    if fin < intervention_deb:  # l'intervention commence sur un autre creneau: préparation du créneau dispo
                        vals['heure_debut'] = deb
                        vals['heure_fin'] = fin
                        vals['duree'] = fin - deb
                        index_courant += 1
                        deb = creneaux_travailles[index_courant][0]  # début courant
                        fin = creneaux_travailles[index_courant][1]  # fin courante
                        while fin < intervention_deb:  # parcourir les créneaux jusqu'à arriver au créneau de l'intervention
                            vals['heure_fin'] = fin
                            vals['duree'] += fin - deb
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
                        vals['heure_fin'] = intervention_deb
                    vals['lieu_debut'] = lieu_deb
                    vals['lieu_fin'] = intervention.address_id and intervention.address_id.get_infos_lieu() or False
                    vals['duree'] += intervention_deb - deb
                    if vals != {} and vals['duree'] >= duree_min:  # un créneau à ajouter
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
            
            return creneaux

        def chevauche_creneau(heures_interv, creneaux):
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

        dt_date_current_naive = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")  # datetime naif
        dt_date_current_utc = pytz.utc.localize(dt_date_current_naive, is_dst=None)  # datetime utc
        dt_date_current_local = dt_date_current_utc.astimezone(tz)  # datetime local
        dt_date_stop_naive = datetime.strptime(date_stop, "%Y-%m-%d %H:%M:%S")  # datetime naif
        dt_date_stop_utc = pytz.utc.localize(dt_date_stop_naive, is_dst=None)  # datetime utc
        dt_date_stop_local = dt_date_stop_utc.astimezone(tz)  # datetime local

        d_date_current = fields.Date.from_string(fields.Datetime.to_string(dt_date_current_local)[:10])
        d_date_stop = fields.Date.from_string(fields.Datetime.to_string(dt_date_stop_local)[:10])

        jours_travailles = []  # liste des jours travaillés
        nb_heures_travaillees = {j: 0 for j in range(1,8)}
        dict_horaires = {}  # dictionnaire contenant les horaires par jour {1: [(9, 12), (14, 18)], 2:[], ...}
        jours_temp_travailles = []  # liste des jours travaillés temporaires
        nb_heures_temp_travaillees = {j: 0 for j in range(1,8)}
        dict_horaires_temp = {}  # dictionnaire contenant les horaires temporaires par jour par équipe {equipe_id: {1: [(9, 12), (14, 18)], 2:[], ...}, ...}
        horaires_temp = False  # passera à True si il faut prendre en compte des horaires temporaires
        equipe_id = equipe.id
        if equipe.mode_horaires == "easy":
            # On utilise le mode facile pour les horaires de cette équipe
            jours_travailles = [jour.numero for jour in equipe.jour_ids] if equipe.jour_ids else range(1, 6)
            for i in range(1,8):
                dict_horaires[i] = []
                if i in jours_travailles:
                    nb_heures_travaillees[i] = round(equipe.hor_mf - equipe.hor_md + equipe.hor_af - equipe.hor_ad, 5)
                    # hor_mf - hor_md > 0 ?
                    if float_compare(equipe.hor_mf, equipe.hor_md, compare_precision)  > 0.0:
                        dict_horaires[i].append((equipe.hor_md, equipe.hor_mf))
                    # hor_af - hor_ad > 0 ?
                    if float_compare(equipe.hor_af, equipe.hor_ad, compare_precision)  > 0.0:
                        dict_horaires[i].append((equipe.hor_ad, equipe.hor_af))
        else: # On utilise le mode avancé pour les horaires de cette équipe
            # l'équipe a-t-elle des horaires temporaires qui peuvent interférer avec ses horaires par défaut sur cette recherche??
            if equipe.creneau_temp_stop and equipe.creneau_temp_stop >= date_start and equipe.creneau_temp_start <= date_stop:
                horaires_temp = True
                str_temp_start = equipe.creneau_temp_start
                d_temp_start = fields.Date.from_string(str_temp_start)
                str_temp_stop = equipe.creneau_temp_stop
                d_temp_stop = fields.Date.from_string(str_temp_stop)
                creneaux_temp_travailles = equipe.creneau_temp_ids
                for i in range(1,8):
                    dict_horaires_temp[i] = []
                    creneaux_temp_du_jour = creneaux_temp_travailles.filtered(lambda x: x.jour_number == i)
                    for c in creneaux_temp_du_jour:
                        nb_heures_temp_travaillees[i] += round(c.heure_fin - c.heure_debut, 5)
                        dict_horaires_temp[i].append((c.heure_debut, c.heure_fin))
                jours_temp_travailles = [j for j in dict_horaires_temp if dict_horaires_temp[j] != []]

            creneaux_travailles = equipe.creneau_ids
            for i in range(1,8):
                dict_horaires[i] = []
                creneaux_du_jour = creneaux_travailles.filtered(lambda x: x.jour_number == i)
                for c in creneaux_du_jour:
                    nb_heures_travaillees[i] += round(c.heure_fin - c.heure_debut, 5)
                    dict_horaires[i].append((c.heure_debut, c.heure_fin))
            jours_travailles = [j for j in dict_horaires if dict_horaires[j] != []]


        un_jour = timedelta(days=1)

        fillerbarzz = []
        creneaux_dispozz = []
        is_jour_temp = False
#float_compare(la_duree_restante, 0.0, compare_precision)  > 0.0
        while d_date_current <= d_date_stop:
            num_jour = d_date_current.isoweekday()
            fillerbar = {
                'nb_heures_travaillees': 0.0,
                'nb_heures_disponibles': 0.0,
                'nb_heures_occupees': 0.0,
                'pct_disponible': 0.0,
                'pct_occupe': 0.0,
            }

            if horaires_temp and d_temp_start <= d_date_current and d_date_current <= d_temp_stop:
                # La date courante est dans les horaires temporaires
                is_jour_temp = True
                fillerbar['nb_heures_travaillees'] = nb_heures_temp_travaillees[num_jour]
                if nb_heures_temp_travaillees[num_jour] == 0.0:
                    journee_debut = False
                    journee_fin = False
                else:
                    journee_debut = dict_horaires_temp[num_jour][0][0]  # heure de début du premier créneau de la journée
                    journee_fin = dict_horaires_temp[num_jour][-1][1]  # heure de fin du dernier créneau de la journée
            else:
                is_jour_temp = False
                fillerbar['nb_heures_travaillees'] = nb_heures_travaillees[num_jour]
                if nb_heures_travaillees[num_jour] == 0.0:
                    journee_debut = False
                    journee_fin = False
                else:
                    journee_debut = dict_horaires[num_jour][0][0]  # heure de début du premier créneau de la journée
                    journee_fin = dict_horaires[num_jour][-1][1]  # heure de fin du dernier créneau de la journée

            if not journee_debut:
                fillerbarzz.append(fillerbar)
                creneaux_dispozz.append([])
                d_date_current += un_jour
                continue

            str_date_current = fields.Date.to_string(d_date_current)
            interventions = intervention_obj.search([('equipe_id', '=', equipe.id),
                                                     ('date', '<=', str_date_current),
                                                     ('date_deadline', '>=', str_date_current),
                                                     ('state', 'in', ('draft', 'confirm', 'done')),
                                                     ], order='date')
            intervention_liste = []
            if not interventions:
                fillerbar['nb_heures_disponibles'] = fillerbar['nb_heures_travaillees']
                fillerbar['pct_disponible'] = 100.0
                fillerbarzz.append(fillerbar)
                d_date_current += un_jour
                if is_jour_temp:
                    creneaux_dispo = get_creneaux_dispo(intervention_liste, dict_horaires_temp[num_jour], 1.0)
                else:
                    creneaux_dispo = get_creneaux_dispo(intervention_liste, dict_horaires[num_jour], 1.0)
                creneaux_dispozz.append(creneaux_dispo)
                continue

            nb_heures_occupees = 0.0
            dt_jour_deb = tz.localize(datetime.strptime(str_date_current+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
            dt_jour_fin = tz.localize(datetime.strptime(str_date_current+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
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
                if intervention_dates[1] <= 0.25:
                    intervention_dates[1] = journee_debut
                if intervention_dates[2] >= 23.75:
                    intervention_dates[2] = journee_fin
                if is_jour_temp:
                    chevauchement = chevauche_creneau((intervention_dates[1], intervention_dates[2]), dict_horaires_temp[num_jour])
                else:
                    chevauchement = chevauche_creneau((intervention_dates[1], intervention_dates[2]), dict_horaires[num_jour])
                nb_heures_occupees += round(intervention_dates[2] - intervention_dates[1] - chevauchement, 5)
                intervention_liste.append(intervention_dates)

            fillerbar['nb_heures_occupees'] = nb_heures_occupees
            fillerbar['pct_occupe'] = fillerbar['nb_heures_occupees'] * 100 / fillerbar['nb_heures_travaillees']
            fillerbar['nb_heures_disponibles'] = fillerbar['nb_heures_travaillees'] - nb_heures_occupees
            if fillerbar['nb_heures_disponibles'] <= 0.0:
                fillerbar['nb_heures_disponibles'] = 0.0
                fillerbar['pct_disponible'] = 0.0
            else:
                fillerbar['pct_disponible'] = fillerbar['nb_heures_disponibles'] * 100 / fillerbar['nb_heures_travaillees']

            fillerbarzz.append(fillerbar)
            if is_jour_temp:
                creneaux_dispo = get_creneaux_dispo(intervention_liste, dict_horaires_temp[num_jour], 0.5)
            else:
                creneaux_dispo = get_creneaux_dispo(intervention_liste, dict_horaires[num_jour], 0.5)
            creneaux_dispozz.append(creneaux_dispo)

            d_date_current += un_jour
        return {'fillerbars': fillerbarzz, 'creneaux_dispo': creneaux_dispozz}

class OFInterventionConfiguration(models.TransientModel):
    _inherit = 'of.intervention.config.settings'

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

    @api.multi
    def set_planningview_filter_client_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.config.settings', 'planningview_filter_client', self.planningview_filter_client)

    @api.multi
    def set_planningview_filter_tache_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.config.settings', 'planningview_filter_tache', self.planningview_filter_tache)

    @api.multi
    def set_planningview_filter_zip_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.config.settings', 'planningview_filter_zip', self.planningview_filter_zip)

    @api.multi
    def set_planningview_filter_city_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.config.settings', 'planningview_filter_city', self.planningview_filter_city)

    @api.multi
    def set_planningview_filter_heure_debut_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.config.settings', 'planningview_filter_heure_debut', self.planningview_filter_heure_debut)

    @api.multi
    def set_planningview_filter_heure_fin_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.config.settings', 'planningview_filter_heure_fin', self.planningview_filter_heure_fin)

    @api.multi
    def set_planningview_filter_duree_defaults(self):
        return self.env['ir.values'].sudo().set_default('of.intervention.config.settings', 'planningview_filter_duree', self.planningview_filter_duree)

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
