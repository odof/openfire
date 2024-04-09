# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from . import survey_user_input_type


class SurveyUserInputQuery(graphene.ObjectType):
    _name = 'SurveyUserInputQuery'
    _type = 'query'

    survey_user_inputs = graphene.List(
        graphene.NonNull(survey_user_input_type.SurveyUserInput),
        filter=graphene.Argument(survey_user_input_type.SurveyUserInputFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_user_inputs(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'like', filter.name)]

        return env['of.survey.user_input'].search(odoo_domain, offset=offset, limit=limit)
