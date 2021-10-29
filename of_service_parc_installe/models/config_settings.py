# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    @api.multi
    def button_prepare_project_issue_migration(self):
        """ Ouvre un wizard pour faire la correspondance de d'étapes Kanban """
        self.ensure_one()
        view_id = self.env.ref('of_service_parc_installe.view_of_project_issue_migration_wizard_form').id
        # supprimer le éventuelles ligne existantes par sécurité,
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
