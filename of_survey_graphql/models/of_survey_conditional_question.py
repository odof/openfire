# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


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

        if answers := args.get('answers'):
            mutation['answer_ids'] = x2many(self=self, model='of.survey.question.answer', input=answers)

        return mutation
