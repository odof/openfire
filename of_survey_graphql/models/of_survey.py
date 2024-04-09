# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFSurveySurvey(models.Model):
    _inherit = 'of.survey.survey'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if title := args.get('title'):
            mutation['title'] = title

        if 'active' in args:
            mutation['active'] = args['active']

        if 'question_pages' in args:
            mutation['question_and_page_ids'] = x2many(
                self=self, model='of.survey.question', input=args.get('question_pages')
            )

        if 'user_inputs' in args:
            mutation['user_input_ids'] = x2many(self=self, model='of.survey.user_input', input=args.get('user_inputs'))

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.survey.survey', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.title:
                odoo_domain += [('title', 'like', select.name)]

        return odoo_domain
