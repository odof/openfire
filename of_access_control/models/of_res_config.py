# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    activate_rules = fields.Boolean(
        string=u"(OF) Cloisonner", help=u"Cocher pour activer les règles de cloisonnement pour les objets du planning.")

    @api.multi
    def set_activate_rules_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'activate_rules', self.activate_rules)

    @api.multi
    def set_company_choice_defaults(self):
        # Il faut désactiver les règles d'accès si on est en choix de société en fonction du contact
        active = self.company_choice == 'user' and self.activate_rules
        rules = self.env['ir.rule']
        # interventions, service, SAV et parc installé
        rules |= self.env.ref('of_access_control.of_planning_intervention_comp_rule')
        rules |= self.env.ref('of_access_control.of_service_comp_rule')
        rules |= self.env.ref('of_access_control.of_project_issue_comp_rule')
        rules |= self.env.ref('of_access_control.of_parc_installe_comp_rule')
        rules.sudo().write({'active': active})
        return super(OfInterventionSettings, self).set_company_choice_defaults()
