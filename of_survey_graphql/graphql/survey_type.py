# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from . import survey_question_page_type, survey_user_input_type


class Survey(OdooObjectType):
    _name = 'Survey'
    _type = 'types'

    id = graphene.Int(required=True)
    title = graphene.String()
    active = graphene.Boolean()
    question_and_pages = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPage))
    user_inputs = graphene.List(graphene.NonNull(survey_user_input_type.SurveyUserInput))

    @staticmethod
    def resolve_question_and_pages(root, info):
        return root.question_and_page_ids or []

    @staticmethod
    def resolve_user_inputs(root, info):
        return root.user_input_ids or []


class SurveyInput(graphene.InputObjectType):
    _name = 'SurveyInput'
    _type = 'types'

    id = graphene.Int()
    title = graphene.String()


class SurveyFilterInput(SurveyInput):
    _name = 'SurveyFilterInput'


class SurveyCreateInput(SurveyInput):
    _name = 'SurveyCreateInput'


class SurveyUpdateInput(SurveyInput):
    _name = 'SurveyUpdateInput'
