# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class OFTourPlanningWizardMixin(models.AbstractModel):
    _inherit = 'of.tour.planning.wizard.mixin'

    def _get_new_values_for_intervention(self, line):
        """ Get the new values for intervention of the reorganized tour line.
        This method can be overridden to add new values to the intervention during the optimization process.
        """
        intervention_values = super(OFTourPlanningWizardMixin, self)._get_new_values_for_intervention(line)
        recurring_intervention = self.env['of.planning.intervention'].search([
            ('employee_ids', 'in', line.wizard_id.tour_id.employee_id.id),
            ('date', '<=', line.wizard_id.tour_id.date),
            ('date_deadline', '>=', line.wizard_id.tour_id.date)], order='date').filtered(
            lambda i: i.date == intervention_values['date'])
        if recurring_intervention:
            intervention_values['verif_dispo'] = False
        return intervention_values
