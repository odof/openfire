# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningTask(models.Model):
    _inherit = 'of.planning.task'

    @api.model
    def _get_minimal_task_duration(self):
        return self.search([], limit=1, order='duration asc').duration or 0

    @api.model_create_multi
    def create(self, vals_list):
        minimum_duration = self._get_minimal_task_duration()
        reorganization_needed = any(
            # The minimum duration has changed, a reorganization of available slots is needed
            'duration' in vals and minimum_duration > vals['duration']
            for vals in vals_list
        )
        if reorganization_needed:
            self.env['of.planning.tour'].search([('date', '>=', fields.Date.today())])._reorganize_available_slot()
        return super().create(vals_list)

    def write(self, vals):
        reorganization_needed = (
            # The minimum duration has changed, a reorganization of available slots is needed
            'duration' in vals
            and self._get_minimal_task_duration() > vals['duration']
        )
        result = super().write(vals)
        if reorganization_needed:
            self.env['of.planning.tour'].search([('date', '>=', fields.Date.today())])._reorganize_available_slot()
        return result

    def unlink(self):
        old_duration = self._get_minimal_task_duration()
        result = super().unlink()
        # The minimum duration has changed, a reorganization of available slots is needed
        if old_duration != self._get_minimal_task_duration():
            self.env['of.planning.tour'].search([('date', '>=', fields.Date.today())])._reorganize_available_slot()
        return result
