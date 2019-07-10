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
        hor_md = equipe.hor_md
        hor_mf = equipe.hor_mf
        hor_ad = equipe.hor_ad
        hor_af = equipe.hor_af

        dt_date_current_naive = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")  # datetime naif
        dt_date_current_utc = pytz.utc.localize(dt_date_current_naive, is_dst=None)  # datetime utc
        dt_date_current_local = dt_date_current_utc.astimezone(tz)  # datetime local
        dt_date_stop_naive = datetime.strptime(date_stop, "%Y-%m-%d %H:%M:%S")  # datetime naif
        dt_date_stop_utc = pytz.utc.localize(dt_date_stop_naive, is_dst=None)  # datetime utc
        dt_date_stop_local = dt_date_stop_utc.astimezone(tz)  # datetime local

        d_date_current = fields.Date.from_string(fields.Datetime.to_string(dt_date_current_local)[:10])
        d_date_stop = fields.Date.from_string(fields.Datetime.to_string(dt_date_stop_local)[:10])


        # @todo: horaires avancés






        delta = (d_date_stop - d_date_current).days
        res = {
            "horaires": [hor_md, hor_mf, hor_ad, hor_af],
            "interventions":[],
            }
        #interv = intervention_obj.search([('equipe_id', '=', equipe.id),('date','!=',False)], limit=1)
        un_jour = timedelta(days=1)

        while d_date_current <= d_date_stop:
            str_date_current = fields.Date.to_string(d_date_current)
            interventions = intervention_obj.search([('equipe_id', '=', equipe.id),
                                                     ('date', '<=', str_date_current),
                                                     ('date_deadline', '>=', str_date_current),
                                                     ('state', 'in', ('draft', 'confirm', 'done')),
                                                     ], order='date')
            intervention_liste = []
            if not interventions:
                res["interventions"].append(intervention_liste)
                d_date_current += un_jour
                continue

            dt_jour_deb = tz.localize(datetime.strptime(str_date_current+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
            dt_jour_fin = tz.localize(datetime.strptime(str_date_current+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
            for intervention in interventions:
                intervention_dates = []
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
                if intervention_dates[0] == 0:
                    intervention_dates[0] = hor_md
                if intervention_dates[1] >= 23.75:
                    intervention_dates[1] = hor_af

                intervention_liste.append(intervention_dates)
            res["interventions"].append(intervention_liste)

            d_date_current += un_jour
        return res

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
