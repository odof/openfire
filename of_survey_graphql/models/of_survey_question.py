# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class OFSurveyQuestion(models.Model):
    _inherit = 'of.survey.question'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if title := args.get('title'):
            mutation['title'] = title
        if sequence := args.get('sequence'):
            mutation['sequence'] = sequence
        if 'is_page' in args.keys():
            mutation['is_page'] = args['is_page']
        if question_type := args.get('question_type'):
            mutation['question_type'] = question_type
        if 'is_conditional' in args.keys():
            mutation['is_conditional'] = args['is_conditional']

        if suggested_answers := args.get('suggested_answers'):
            mutation['suggested_answer_ids'] = x2many(
                self=self, model='of.survey.question.answer', input=suggested_answers
            )

        if user_input_lines := args.get('user_input_line'):
            mutation['user_input_line_ids'] = x2many(
                self=self, model='of.survey.user_input.line', input=user_input_lines
            )

        if conditional_questions := args.get('conditional_questions'):
            mutation['conditional_questions'] = x2many(
                self=self, model='of.survey.conditional.question', input=conditional_questions
            )

        return mutation
