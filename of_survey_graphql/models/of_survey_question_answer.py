# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain


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

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = []

        if domain:
            odoo_domain = graphqlOdooDomain(self=self, model='of.survey.question.answer', domain=domain)

        if select:
            if select.id:
                odoo_domain += [('id', '=', select.id)]
            if select.value:
                odoo_domain += [('value', 'like', select.value)]

        return odoo_domain
