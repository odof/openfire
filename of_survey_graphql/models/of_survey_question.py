# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


class OFSurveyQuestion(models.Model):
    _inherit = 'of.survey.question'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if title := args.get('title'):
            mutation['title'] = title
        if sequence := args.get('sequence'):
            mutation['sequence'] = sequence
        if 'is_page' in args:
            mutation['is_page'] = args['is_page']
        if question_type := args.get('question_type'):
            mutation['question_type'] = question_type
        if 'is_conditional' in args:
            mutation['is_conditional'] = args['is_conditional']

        if 'suggested_answers' in args:
            mutation['suggested_answer_ids'] = x2many(
                self=self, model='of.survey.question.answer', input=args.get('suggested_answers')
            )

        if 'user_input_lines' in args:
            mutation['user_input_line_ids'] = x2many(
                self=self, model='of.survey.user_input.line', input=args.get('user_input_lines')
            )

        if 'conditional_questions' in args:
            mutation['conditional_questions'] = x2many(
                self=self, model='of.survey.conditional.question', input=args.get('conditional_questions')
            )

        if 'validation_required' in args:
            mutation['validation_required'] = args['validation_required']

        if validation_min_float_value := args.get('validation_min_float_value'):
            mutation['validation_min_float_value'] = validation_min_float_value

        if validation_max_float_value := args.get('validation_max_float_value'):
            mutation['validation_max_float_value'] = validation_max_float_value

        if validation_error_msg := args.get('validation_error_msg'):
            mutation['validation_error_msg'] = validation_error_msg

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.survey.question', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
