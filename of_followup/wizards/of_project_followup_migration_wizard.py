# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class OFFollowupProjectMigrationWizard(models.TransientModel):
    _name = 'of.followup.project.migration.wizard'

    def action_start_migration(self):
        self.env['of.followup.project']._followup_data_migration()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
