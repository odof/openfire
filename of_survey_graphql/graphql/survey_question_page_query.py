# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from . import survey_question_page_type


class SurveyConditionalQuestionQuery(graphene.ObjectType):
    _name = 'SurveyConditionalQuestionQuery'
    _type = 'query'

    survey_conditional_questions = graphene.List(
        graphene.NonNull(survey_question_page_type.SurveyConditionalQuestion),
        select=graphene.Argument(survey_question_page_type.SurveyConditionalQuestionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_conditional_questions(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.survey.conditional.question']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.survey.conditional.question'].search(odoo_domain, offset=offset, limit=limit)


class SurveyQuestionPageQuery(graphene.ObjectType):
    _name = 'SurveyQuestionPageQuery'
    _type = 'query'

    survey_question_pages = graphene.List(
        graphene.NonNull(survey_question_page_type.SurveyQuestionPage),
        select=graphene.Argument(survey_question_page_type.SurveyQuestionPageFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_question_pages(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.survey.question']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.survey.question'].search(odoo_domain, offset=offset, limit=limit)
