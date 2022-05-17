# -*- coding: utf-8 -*-

from odoo import models, api


class OFFollowUpProjectSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.multi
    def action_open_followup_migration_wizard(self):
        self.ensure_one()
        view_id = self.env.ref('of_followup.of_project_followup_migration_wizard_form_view').id
        return {
            'name': 'Follow-up migration',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.followup.project.migration.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': self.env.context
        }
