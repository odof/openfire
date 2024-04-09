# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


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

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.planning.task', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'ilike', select.name)]
            if select.duration:
                odoo_domain += [('duration', '=', select.duration)]

        return odoo_domain
