# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


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

        if 'active' in args:
            mutation['active'] = args['active']

        if 'interventions' in args:
            mutation['intervention_ids'] = x2many(self=self, model='calendar.event', input=args.get('interventions'))

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.planning.tag', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
