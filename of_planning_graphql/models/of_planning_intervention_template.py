# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if 'is_default_template' in args.keys():
            mutation['is_default_name'] = args['is_default_template']

        if task := args.get('task'):
            mutation['task_id'] = many2one(self=self, model='of.planning.task', input=task)

        if fiscal_position := args.get('fiscal_position'):
            mutation['fiscal_position_id'] = many2one(self=self, model='account.fiscal.position', input=fiscal_position)

        return mutation
