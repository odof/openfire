# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.image_type import Image, ImageInput

from . import survey_question_answer_type


class SurveyUserInputLine(OdooObjectType):
    _name = "SurveyUserInputLine"
    _type = "types"

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
    comment = graphene.String()

    @staticmethod
    def resolve_suggested_answer(root, info):
        return root.suggested_answer_id or None

    @staticmethod
    def resolve_images(root, info):
        return root.value_image_ids or []

    @staticmethod
    def resolve_comment(root, info):
        env = info.context["env"]
        if question := env["of.survey.question"].browse(root.question_id.id):
            # Resolving comment only for simple_choice, multiple_choice questions with answer_type = 'char_box'
            if question.question_type in ["simple_choice", "multiple_choice"] and root.answer_type == "char_box":
                return root.value_char_box
            else:
                return None
        else:
            return None


class SurveyUserInputLineInput(graphene.InputObjectType):
    _name = "SurveyUserInputLineInput"
    _type = "types"

    id = graphene.Int()
    skipped = graphene.Boolean()
    answer_type = graphene.String()
    value_char_box = graphene.String()
    value_date = graphene.Date()
    value_text_box = graphene.String()
    value_numerical_box = graphene.Float()
    suggested_answer = graphene.Field(survey_question_answer_type.SurveyQuestionAnswerInput)
    question = graphene.Int(description="Identifiant de la question à laquelle cette ligne répond")
    images = graphene.List(graphene.NonNull(ImageInput))
    comment = graphene.String()


class SurveyUserInputLineFilterInput(SurveyUserInputLineInput):
    _name = "SurveyUserInputLineFilterInput"
