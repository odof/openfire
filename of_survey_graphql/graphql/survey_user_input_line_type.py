# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from . import survey_question_answer_type


class SurveyUserInputLine(OdooObjectType):
    _name = 'SurveyUserInputLine'
    _type = 'types'

    id = graphene.Int(required=True)
    skipped = graphene.Boolean()
    answer_type = graphene.String()
    value_char_box = graphene.String()
    value_date = graphene.Date()
    value_text_box = graphene.String()
    suggested_answer = graphene.Field(survey_question_answer_type.SurveyQuestionAnswer)

    @staticmethod
    def resolve_suggested_answer(root, info):
        return root.suggested_answer_id or None


class SurveyUserInputLineInput(graphene.InputObjectType):
    _name = 'SurveyUserInputLineInput'
    _type = 'types'

    id = graphene.Int()
    skipped = graphene.Boolean()
    answer_type = graphene.String()
    value_char_box = graphene.String()
    value_date = graphene.Date()
    value_text_box = graphene.String()


class SurveyUserInputLineFilterInput(SurveyUserInputLineInput):
    _name = 'SurveyUserInputLineFilterInput'


class SurveyUserInputLineCreateInput(SurveyUserInputLineInput):
    _name = 'SurveyUserInputLineCreateInput'


class SurveyUserInputLineUpdateInput(SurveyUserInputLineInput):
    _name = 'SurveyUserInputLineUpdateInput'
