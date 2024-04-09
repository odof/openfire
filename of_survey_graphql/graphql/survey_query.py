# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from . import survey_type


class SurveyQuery(graphene.ObjectType):
    _name = 'SurveyQuery'
    _type = 'query'

    surveys = graphene.List(
        graphene.NonNull(survey_type.Survey),
        select=graphene.Argument(survey_type.SurveyFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_surveys(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.survey.survey']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.survey.survey'].search(odoo_domain, offset=offset, limit=limit)
