# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if survey := args.get('survey'):
            mutation['of_survey_id'] = many2one(self=self, model='of.survey.survey', input=survey)

        return mutation
