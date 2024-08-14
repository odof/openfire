# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

convert_type_dict = {
    'simple_choice': 'suggestion',
    'multiple_choice': 'suggestion',
    'text_box': 'text_box',
    'char_box': 'char_box',
    'date': 'date',
    'multi_image': 'multi_image',
    'form': 'form',
    'numerical_box': 'numerical_box',
}


class OFSurveyUserInputLine(models.Model):
    _inherit = 'of.survey.user_input.line'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if 'skipped' in args:
            mutation['skipped'] = args['skipped']

        if 'answer_type' in args:
            mutation['answer_type'] = args['answer_type']

        elif question_id := args.get('question'):
            if question_id:
                # on va chercher le type sur la question
                odoo_question = self.env['of.survey.question'].browse(question_id)
                if odoo_question.question_type in convert_type_dict:
                    mutation['answer_type'] = convert_type_dict[odoo_question.question_type]

        if value_char_box := args.get('value_char_box'):
            mutation['value_char_box'] = value_char_box

        if value_date := args.get('value_date'):
            mutation['value_date'] = value_date

        if value_text_box := args.get('value_text_box'):
            mutation['value_text_box'] = value_text_box

        if value_numerical_box := args.get('value_numerical_box'):
            mutation['value_numerical_box'] = value_numerical_box

        if suggested_answer := args.get('suggested_answer'):
            mutation['suggested_answer_id'] = many2one(
                self=self, model='of.survey.question.answer', input=suggested_answer
            )

        if question_id := args.get('question'):
            mutation['question_id'] = question_id

        if 'images' in args:
            mutation['value_image_ids'] = x2many(self=self, model='of.image', input=args.get('images'))

        return mutation

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.survey.user_input.line', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.name:
                odoo_domain += [('name', 'like', select.name)]

        return odoo_domain
