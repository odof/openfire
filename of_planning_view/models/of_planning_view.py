# -*- coding: utf-8 -*-

from odoo.osv import orm
from odoo import models, fields, api

PLANNING_VIEW = ('planning', 'Planning')

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
