# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OFProjectIssueMigrationWizard(models.TransientModel):
    _name = 'of.project.issue.migration.wizard'

    kanban_step_line_ids = fields.One2many(
        string=u"correspondance d'étapes kanban", comodel_name='of.project.issue.migration.wizard.step.line',
        inverse_name='wizard_id')

    def button_launch_migration(self):
        self.env['project.issue'].migrer_sav_di()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class OFProjectIssueMigrationWizardStepLine(models.TransientModel):
    _name = 'of.project.issue.migration.wizard.step.line'

    wizard_id = fields.Many2one(string=u"Wizard", comodel_name='of.project.issue.migration.wizard')
    sav_step_id = fields.Many2one(string=u"Étape SAV", comodel_name='project.task.type', readonly=True)
    service_step_id = fields.Many2one(string=u"Étape DI", comodel_name='of.service.stage')
