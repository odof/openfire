# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFProjectPlanningAccountAnalyticLineHook(models.AbstractModel):
    _name = 'of.project.planning.account.analytic.line.hook'

    @api.model
    def post_hook(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_project_planning'), ('state', 'in', ['installed', 'to upgrade'])])
        if module_self:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_self.latest_version
            if version < '10.0.2.1':
                # connection activités planifiées et feuilles de temps existantes
                lines = self.env['account.analytic.line'].search([('sheet_id.state', 'in', ('draft', 'new'))])
                for line in lines:
                    line._onchange_period_params()
