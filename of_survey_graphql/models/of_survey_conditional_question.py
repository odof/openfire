# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFSurveyConditionalQuestion(models.Model):
    _inherit = 'of.survey.conditional.question'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if operator := args.get('operator'):
            mutation['operator'] = operator

        if question := args.get('question'):
            mutation['question_id'] = many2one(self=self, model='of.survey.question', input=question)

        if triggering_question := args.get('triggering_question'):
            mutation['triggering_question_id'] = many2one(
                self=self, model='of.survey.question', input=triggering_question
            )

        if 'answers' in args.keys():
            mutation['answer_ids'] = x2many(self=self, model='of.survey.question.answer', input=args.get('answers'))

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.survey.conditional.question', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
