# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import x2many


class OFSurveySurvey(models.Model):
    _inherit = 'of.survey.survey'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if title := args.get('title'):
            mutation['title'] = title

        if 'active' in args.keys():
            mutation['active'] = args['active']

        if question_pages := args.get('question_pages'):
            mutation['question_and_page_ids'] = x2many(self=self, model='of.survey.question', input=question_pages)

        if user_inputs := args.get('user_inputs'):
            mutation['user_input_ids'] = x2many(self=self, model='of.survey.user_input', input=user_inputs)

        return mutation
