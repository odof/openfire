# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFSurveyQuestionAnswer(models.Model):
    _inherit = 'of.survey.question.answer'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if value := args.get('value'):
            mutation['value'] = value

        if sequence := args.get('sequence'):
            mutation['sequence'] = sequence

        if is_correct := args.get('is_correct'):
            mutation['is_correct'] = is_correct

        if is_default := args.get('is_default'):
            mutation['is_default'] = is_default

        return mutation
