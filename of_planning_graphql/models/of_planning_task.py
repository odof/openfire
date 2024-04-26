# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFPlanningTask(models.Model):
    _inherit = 'of.planning.task'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if description := args.get('description'):
            mutation['description'] = description

        if duration := args.get('duration'):
            mutation['duration'] = duration

        return mutation
