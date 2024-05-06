# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


class OFSurveyUserInput(models.Model):
    _name = 'of.survey.user_input'
    _inherit = 'of.survey.user_input'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if state := args.get('state'):
            mutation['state'] = state

        if email := args.get('email'):
            mutation['email'] = email

        if partner := args.get('partner'):
            mutation['partner_id'] = many2one(self=self, model='res.partner', input=partner)

        if 'user_input_lines' in args.keys():
            mutation['user_input_line_ids'] = x2many(
                self=self, model='of.survey.user_input.line', input=args.get('user_input_lines')
            )

        if 'predefined_questions' in args.keys():
            mutation['predefined_question_ids'] = x2many(
                self=self, model='of.survey.question', input=args.get('predefined_questions')
            )

        return mutation
