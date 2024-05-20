# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class OFPlanningTag(models.Model):
    _inherit = 'of.planning.tag'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if sequence := args.get('sequence'):
            mutation['sequence'] = sequence

        if color := args.get('color'):
            mutation['color'] = color

        if 'active' in args.keys():
            mutation['active'] = args['active']

        if 'interventions' in args.keys():
            mutation['intervention_ids'] = x2many(self=self, model='calendar.event', input=args.get('interventions'))

        return mutation
