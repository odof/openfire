# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from . import survey_user_input_type


class SurveyUserInputQuery(graphene.ObjectType):
    _name = 'SurveyUserInputQuery'
    _type = 'query'

    survey_user_inputs = graphene.List(
        graphene.NonNull(survey_user_input_type.SurveyUserInput),
        select=graphene.Argument(survey_user_input_type.SurveyUserInputFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_user_inputs(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.survey.user_input']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.survey.user_input'].search(odoo_domain, offset=offset, limit=limit)
