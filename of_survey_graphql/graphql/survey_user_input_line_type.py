# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.image_type import Image

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
    value_numerical_box = graphene.Float()
    suggested_answer = graphene.Field(survey_question_answer_type.SurveyQuestionAnswer)
    question_id = graphene.NonNull(graphene.Int, description="Identifiant de la question à laquelle cette ligne répond")
    images = graphene.NonNull(graphene.List(graphene.NonNull(Image)))

    @staticmethod
    def resolve_suggested_answer(root, info):
        return root.suggested_answer_id or None

    @staticmethod
    def resolve_images(root, info):
        return root.value_image_ids or []


class SurveyUserInputLineInput(graphene.InputObjectType):
    _name = 'SurveyUserInputLineInput'
    _type = 'types'

    id = graphene.Int()
    skipped = graphene.Boolean()
    answer_type = graphene.String()
    value_char_box = graphene.String()
    value_date = graphene.Date()
    value_text_box = graphene.String()
    value_numerical_box = graphene.Float()
    suggested_answer = graphene.Field(survey_question_answer_type.SurveyQuestionAnswerInput)


class SurveyUserInputLineFilterInput(SurveyUserInputLineInput):
    _name = 'SurveyUserInputLineFilterInput'
