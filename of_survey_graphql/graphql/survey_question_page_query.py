# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from . import survey_question_page_type


class SurveyConditionalQuestionQuery(graphene.ObjectType):
    _name = 'SurveyConditionalQuestionQuery'
    _type = 'query'

    survey_conditional_questions = graphene.List(
        graphene.NonNull(survey_question_page_type.SurveyConditionalQuestion),
        filter=graphene.Argument(survey_question_page_type.SurveyConditionalQuestionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_conditional_questions(root, info, filter=None, domain=None, offset=0, limit=10):
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

        return env['of.survey.conditional.question'].search(odoo_domain, offset=offset, limit=limit)


class SurveyQuestionPageQuery(graphene.ObjectType):
    _name = 'SurveyQuestionPageQuery'
    _type = 'query'

    survey_question_pages = graphene.List(
        graphene.NonNull(survey_question_page_type.SurveyQuestionPage),
        filter=graphene.Argument(survey_question_page_type.SurveyQuestionPageFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_question_pages(root, info, filter=None, domain=None, offset=0, limit=10):
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

        return env['of.survey.question'].search(odoo_domain, offset=offset, limit=limit)
