# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    group_of_group_planning_intervention_google = fields.Boolean(
        string=u"Manage Google events",
        implied_group='of_planning_google.of_group_planning_intervention_google')

    @api.onchange('group_of_group_planning_intervention_recurring')
    def _onchange_group_of_group_planning_intervention_recurring(self):
        if not self.group_of_group_planning_intervention_recurring:
            self.group_of_group_planning_intervention_google = False
