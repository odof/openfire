# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from . import survey_type


class SurveyQuery(graphene.ObjectType):
    _name = 'SurveyQuery'
    _type = 'query'

    surveys = graphene.List(
        graphene.NonNull(survey_type.Survey),
        filter=graphene.Argument(survey_type.SurveyFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_surveys(root, info, filter=None, domain=None, offset=0, limit=10):
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
            if filter.title:
                odoo_domain += [('title', 'like', filter.name)]

        return env['of.survey.survey'].search(odoo_domain, offset=offset, limit=limit)
