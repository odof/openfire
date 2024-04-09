import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from . import (
    survey_question_answer_mutation,
    survey_question_answer_type,
    survey_question_page_mutation,
    survey_question_page_type,
    survey_user_input_line_type,
)


class SurveyUserInputLineCreate(graphene.Mutation):
    _name = 'SurveyUserInputLineCreate'

    class Arguments:
        input = survey_user_input_line_type.SurveyUserInputLineCreateInput(required=True)
        suggested_answer = survey_question_answer_type.SurveyQuestionAnswerInput()
        question = survey_question_page_type.SurveyQuestionPageInput()

    Output = survey_user_input_line_type.SurveyUserInputLine

    def mutate(self, info, input, suggested_answer=None, question=None):
        env = info.context["env"]

        if suggested_answer:
            if suggested_answer.id:
                suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerUpdate().mutate(
                    info, id=suggested_answer.id, input=suggested_answer
                )
            else:
                suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerCreate().mutate(
                    info, input=suggested_answer
                )

        if question:
            if question.id:
                question = survey_question_page_mutation.SurveyQuestionPageUpdate().mutate(
                    info, id=question.id, input=question
                )
            else:
                question = survey_question_page_mutation.SurveyQuestionPageCreate().mutate(info, input=question)

        survey_user_input_line = lazy_create(env, 'of.survey.user_input.line', input)

        if suggested_answer:
            survey_user_input_line.suggested_answer_id = suggested_answer

        if question:
            survey_user_input_line.question_id = question

        return survey_user_input_line


class SurveyUserInputLineUpdate(graphene.Mutation):
    _name = 'SurveyUserInputLineUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = survey_user_input_line_type.SurveyUserInputLineUpdateInput(required=True)
        suggested_answer = survey_question_answer_type.SurveyQuestionAnswerInput()
        question = survey_question_page_type.SurveyQuestionPageInput()

    Output = survey_user_input_line_type.SurveyUserInputLine

    def mutate(self, info, id, input, suggested_answer=None, question=None):
        env = info.context["env"]

        if suggested_answer:
            if suggested_answer.id:
                suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerUpdate().mutate(
                    info, id=suggested_answer.id, input=suggested_answer
                )
            else:
                suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerCreate().mutate(
                    info, input=suggested_answer
                )

        if question:
            if question.id:
                question = survey_question_page_mutation.SurveyQuestionPageUpdate().mutate(
                    info, id=question.id, input=question
                )
            else:
                question = survey_question_page_mutation.SurveyQuestionPageCreate().mutate(info, input=question)

        survey_user_input_line = lazy_update(env, 'of.survey.user_input.line', id, input)

        if suggested_answer:
            survey_user_input_line.suggested_answer_id = suggested_answer

        if question:
            survey_user_input_line.question_id = question

        return survey_user_input_line


class SurveyUserInputLineDelete(graphene.Mutation):
    _name = 'SurveyUserInputLineDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = survey_user_input_line_type.SurveyUserInputLine

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.survey.user_input.line', id)


class SurveyUserInputLineMutation(graphene.ObjectType):
    _name = 'SurveyUserInputLineMutation'
    _type = 'mutation'

    survey_user_input_line_create = SurveyUserInputLineCreate.Field()
    survey_user_input_line_update = SurveyUserInputLineUpdate.Field()
    survey_user_input_line_delete = SurveyUserInputLineDelete.Field()
