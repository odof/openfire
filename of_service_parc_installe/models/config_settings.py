# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.model
    def _init_group_of_project_issue_not_migrated(self):
        # On utilise une fonction déclenchée par le XML plutôt qu'un auto_init,
        # car au moment de l'auto_init, le groupe n'existe pas encore
        # Si la migration n'a pas été faite, ajouter le groupe project_issue_not_migrated à tous les utilisateurs
        if not self.env['ir.config_parameter'].sudo().get_param('of_migration_sav_di'):
            group_not_migrated = self.env.ref('of_service_parc_installe.group_of_project_issue_not_migrated')
            group_user = self.env.ref('base.group_user')
            if group_not_migrated not in group_user.implied_ids:
                group_user.write({'implied_ids': [(4, group_not_migrated.id)]})

    @api.multi
    def button_prepare_project_issue_migration(self):
        """ Ouvre un wizard pour faire la correspondance des étapes Kanban """
        self.ensure_one()
        view_id = self.env.ref('of_service_parc_installe.view_of_project_issue_migration_wizard_form').id
        # Supprimer les éventuelles lignes existantes par sécurité,
        # ces lignes sont utilisées ensuite dans la méthode migrer_sav_di
        self.env['of.project.issue.migration.wizard.step.line'].search([]).unlink()
        kanban_step_line_ids = []
        sav_steps = self.env['project.task.type'].search([])
        for sav_step in sav_steps:
            kanban_step_line_ids.append((0, 0, {'sav_step_id': sav_step.id}))
        wizard = self.env['of.project.issue.migration.wizard'].create({
            'kanban_step_line_ids': kanban_step_line_ids,
        })
        return {
            'name': 'Migration des SAV',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.project.issue.migration.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context}
