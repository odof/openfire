# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from . import survey_question_answer_type, survey_user_input_line_type


class SurveyQuestionPage(OdooObjectType):
    _name = 'SurveyQuestionPage'
    _type = 'types'

    id = graphene.Int(required=True)
    title = graphene.NonNull(graphene.String)
    sequence = graphene.Int()
    is_page = graphene.Boolean()
    question_type = graphene.String()
    is_conditional = graphene.Boolean()
    validation_email = graphene.Boolean()
    page_id = graphene.Int()
    suggested_answer_ids = graphene.List(
        graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswer), name="suggestedAnswers"
    )

    user_input_line_ids = graphene.List(
        graphene.NonNull(survey_user_input_line_type.SurveyUserInputLine), name="userInputLines"
    )

    conditional_questions = graphene.List(
        graphene.NonNull(lambda: SurveyConditionalQuestion), name="conditionalQuestions"
    )


class SurveyConditionalQuestion(OdooObjectType):
    _name = 'SurveyConditionalQuestion'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()
    operator = graphene.String()
    question_id = graphene.Field(SurveyQuestionPage, name="question")
    triggering_question_id = graphene.Field(SurveyQuestionPage, name="triggeringQuestion")
    answer_ids = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswer), name="answers")


class SurveyQuestionPageInput(graphene.InputObjectType):
    _name = 'SurveyQuestionPageInput'
    _type = 'types'

    id = graphene.Int()
    title = graphene.String()
    sequence = graphene.Int()
    is_page = graphene.Boolean()
    question_type = graphene.String()
    is_conditional = graphene.Boolean()
    suggested_answer_ids = graphene.List(
        graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput), name="suggestedAnswers"
    )

    user_input_line_ids = graphene.List(
        graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput), name="userInputLines"
    )

    conditional_questions = graphene.List(
        graphene.NonNull(lambda: SurveyConditionalQuestionInput), name="conditionalQuestions"
    )


class SurveyConditionalQuestionInput(graphene.InputObjectType):
    _name = 'SurveyConditionalQuestionInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    operator = graphene.String()
    question_id = graphene.Field(SurveyQuestionPageInput, name="question")
    triggering_question_id = graphene.Field(SurveyQuestionPageInput, name="triggeringQuestion")
    answer_ids = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput), name="answers")


class SurveyConditionalQuestionFilterInput(graphene.InputObjectType):
    _name = 'SurveyConditionalQuestionFilterInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    operator = graphene.String()


class SurveyQuestionPageFilterInput(graphene.InputObjectType):
    _name = 'SurveyQuestionPageFilterInput'
    _type = 'types'

    id = graphene.Int()
    title = graphene.String()
    sequence = graphene.Int()
    is_page = graphene.Boolean()
    question_type = graphene.String()
    is_conditional = graphene.Boolean()
