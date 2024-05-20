# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFSurveyUserInputLine(models.Model):
    _inherit = 'of.survey.user_input.line'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if 'skipped' in args.keys():
            mutation['skipped'] = args['skipped']

        if answer_type := args.get('answer_type'):
            mutation['answer_type'] = answer_type

        if value_char_box := args.get('value_char_box'):
            mutation['value_char_box'] = value_char_box

        if value_date := args.get('value_date'):
            mutation['value_date'] = value_date

        if value_text_box := args.get('value_text_box'):
            mutation['value_text_box'] = value_text_box

        if suggested_answer := args.get('suggested_answer'):
            mutation['suggested_answer_id'] = many2one(
                self=self, model='of.survey.question.answer', input=suggested_answer
            )

        if question := args.get('question'):
            mutation['question_id'] = many2one(self=self, model='of.survey.question', input=question)

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.survey.user_input.line', domain=domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'like', filter.name)]

        return odoo_domain
