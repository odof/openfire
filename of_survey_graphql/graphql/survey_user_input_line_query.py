# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from . import survey_user_input_line_type


class SurveyUserInputLineQuery(graphene.ObjectType):
    _name = 'SurveyUserInputLineQuery'
    _type = 'query'

    survey_user_input_lines = graphene.List(
        graphene.NonNull(survey_user_input_line_type.SurveyUserInputLine),
        select=graphene.Argument(survey_user_input_line_type.SurveyUserInputLineFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_user_input_lines(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.survey.user_input.line']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.survey.user_input.line'].search(odoo_domain, offset=offset, limit=limit)
