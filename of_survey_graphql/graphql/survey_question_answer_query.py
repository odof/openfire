# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from . import survey_question_answer_type


class SurveyQuestionAnswerQuery(graphene.ObjectType):
    _name = "SurveyQuestionAnswerQuery"
    _type = "query"

    survey_question_answers = graphene.List(
        graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswer),
        select=graphene.Argument(survey_question_answer_type.SurveyQuestionAnswerFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_question_answers(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["of.survey.question.answer"]._prepare_graphql_domain(select=select, domain=domain)

        return env["of.survey.question.answer"].search(odoo_domain, offset=offset, limit=limit)
