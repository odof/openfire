# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from . import survey_question_answer_type


class SurveyQuestionAnswerQuery(graphene.ObjectType):
    _name = 'SurveyQuestionAnswerQuery'
    _type = 'query'

    survey_question_answers = graphene.List(
        graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswer),
        filter=graphene.Argument(survey_question_answer_type.SurveyQuestionAnswerFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_survey_question_answers(root, info, filter=None, domain=None, offset=0, limit=10):
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
            if filter.value:
                odoo_domain += [('value', 'like', filter.value)]

        return env['of.survey.question.answer'].search(odoo_domain, offset=offset, limit=limit)
