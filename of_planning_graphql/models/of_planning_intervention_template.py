# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if 'is_default_template' in args:
            mutation['is_default_name'] = args['is_default_template']

        if task := args.get('task'):
            mutation['task_id'] = many2one(self=self, model='of.planning.task', input=task)

        if fiscal_position := args.get('fiscal_position'):
            mutation['fiscal_position_id'] = many2one(self=self, model='account.fiscal.position', input=fiscal_position)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.planning.intervention.template', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'ilike', select.name)]
            if select.is_default_template:
                odoo_domain += [('is_default_template', '=', select.is_default_template)]

        return odoo_domain
