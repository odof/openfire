import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from . import (
    survey_question_answer_mutation,
    survey_question_answer_type,
    survey_question_page_type,
    survey_user_input_line_mutation,
    survey_user_input_line_type,
)


class SurveyConditionalQuestionCreate(graphene.Mutation):
    _name = 'SurveyConditionalQuestionCreate'

    class Arguments:
        input = survey_question_page_type.SurveyConditionalQuestionCreateInput(required=True)
        question = survey_question_page_type.SurveyQuestionPageInput()
        triggering_question = survey_question_page_type.SurveyQuestionPageInput()
        answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))

    Output = survey_question_page_type.SurveyConditionalQuestion

    def mutate(self, info, input, question=None, triggering_question=None, answers=None):
        env = info.context["env"]

        if question:
            if question.id:
                question = SurveyQuestionPageUpdate().mutate(info, id=question.id, input=question)
            else:
                question = SurveyQuestionPageCreate().mutate(info, input=question)

        if triggering_question:
            if triggering_question.id:
                triggering_question = SurveyQuestionPageUpdate().mutate(
                    info, id=triggering_question.id, input=triggering_question
                )
            else:
                triggering_question = SurveyQuestionPageCreate().mutate(info, input=triggering_question)

        create_answers = env['of.survey.question.answer']

        if answers:
            for answer in answers:
                if answer.id:
                    # on est sur une mise à jour
                    answer = survey_question_answer_mutation.SurveyQuestionAnswerUpdate().mutate(
                        info, id=answer.id, input=answer
                    )
                else:
                    answer = survey_question_answer_mutation.SurveyQuestionAnswerCreate().mutate(info, input=answer)
                create_answers += answer

        survey_conditional_question = lazy_create(env, 'of.survey.conditional.question', input)

        if question:
            survey_conditional_question.question_id = question

        if triggering_question:
            survey_conditional_question.triggering_question_id = triggering_question

        if create_answers:
            survey_conditional_question.answer_ids = [(6, 0, create_answers.ids)]

        return survey_conditional_question


class SurveyConditionalQuestionUpdate(graphene.Mutation):
    _name = 'SurveyConditionalQuestionUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = survey_question_page_type.SurveyConditionalQuestionUpdateInput(required=True)
        question = survey_question_page_type.SurveyQuestionPageInput()
        triggering_question = survey_question_page_type.SurveyQuestionPageInput()
        answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))

    Output = survey_question_page_type.SurveyConditionalQuestion

    def mutate(self, info, id, input, question=None, triggering_question=None, answers=None):
        env = info.context["env"]

        if question:
            if question.id:
                question = SurveyQuestionPageUpdate().mutate(info, id=question.id, input=question)
            else:
                question = SurveyQuestionPageCreate().mutate(info, input=question)

        if triggering_question:
            if triggering_question.id:
                triggering_question = SurveyQuestionPageUpdate().mutate(
                    info, id=triggering_question.id, input=triggering_question
                )
            else:
                triggering_question = SurveyQuestionPageCreate().mutate(info, input=triggering_question)

        update_answers = env['of.survey.question.answer']

        if answers:
            for answer in answers:
                if answer.id:
                    # on est sur une mise à jour
                    answer = survey_question_answer_mutation.SurveyQuestionAnswerUpdate().mutate(
                        info, id=answer.id, input=answer
                    )
                else:
                    answer = survey_question_answer_mutation.SurveyQuestionAnswerCreate().mutate(info, input=answer)
                update_answers += answer

        survey_conditional_question = lazy_update(env, 'of.survey.conditional.question', id, input)

        if question:
            survey_conditional_question.question_id = question

        if triggering_question:
            survey_conditional_question.triggering_question_id = triggering_question

        if update_answers:
            survey_conditional_question.answer_ids = [(6, 0, update_answers.ids)]

        return survey_conditional_question


class SurveyConditionalQuestionDelete(graphene.Mutation):
    _name = 'SurveyConditionalQuestionDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = survey_question_page_type.SurveyConditionalQuestion

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.survey.conditional.question', id)


class SurveyConditionalQuestionMutation(graphene.ObjectType):
    _name = 'SurveyConditionalQuestionMutation'
    _type = 'mutation'

    survey_conditional_question_create = SurveyConditionalQuestionCreate.Field()
    survey_conditional_question_update = SurveyConditionalQuestionUpdate.Field()
    survey_conditional_question_delete = SurveyConditionalQuestionDelete.Field()


class SurveyQuestionPageCreate(graphene.Mutation):
    _name = 'SurveyQuestionPageCreate'

    class Arguments:
        input = survey_question_page_type.SurveyQuestionPageCreateInput(required=True)
        suggested_answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        conditional_questions = graphene.List(
            graphene.NonNull(survey_question_page_type.SurveyConditionalQuestionInput)
        )

    Output = survey_question_page_type.SurveyQuestionPage

    def mutate(self, info, input, suggested_answers=None, user_input_lines=None, conditional_questions=None):
        env = info.context["env"]

        create_suggested_answers = env['of.survey.question.answer']

        if suggested_answers:
            for suggested_answer in suggested_answers:
                if suggested_answer.id:
                    # on est sur une mise à jour
                    suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerUpdate().mutate(
                        info, id=suggested_answer.id, input=suggested_answer
                    )
                else:
                    suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerCreate().mutate(
                        info, input=suggested_answer
                    )
                create_suggested_answers += suggested_answer

        create_user_input_lines = env['of.survey.user_input.line']

        if user_input_lines:
            for user_input_line in user_input_lines:
                if user_input_line.id:
                    # on est sur une mise à jour
                    user_input_line = survey_user_input_line_mutation.SurveyUserInputLineUpdate().mutate(
                        info, id=user_input_line.id, input=user_input_line
                    )
                else:
                    user_input_line = survey_user_input_line_mutation.SurveyUserInputLineCreate().mutate(
                        info, input=user_input_line
                    )
                create_user_input_lines += user_input_line

        create_conditional_questions = env['of.survey.conditional.question']

        if conditional_questions:
            for conditional_question in conditional_questions:
                if conditional_question.id:
                    # on est sur une mise à jour
                    conditional_question = SurveyConditionalQuestionUpdate().mutate(
                        info, id=conditional_question.id, input=conditional_question
                    )
                else:
                    conditional_question = SurveyConditionalQuestionCreate().mutate(info, input=conditional_question)
                create_conditional_questions += conditional_question

        survey_question_page = lazy_create(env, 'of.survey.question', input)

        if create_suggested_answers:
            survey_question_page.suggested_answer_ids = [(6, 0, create_suggested_answers.ids)]

        if create_user_input_lines:
            survey_question_page.user_input_line_ids = [(6, 0, create_user_input_lines.ids)]

        if create_conditional_questions:
            survey_question_page.conditional_questions = [(6, 0, create_conditional_questions.ids)]

        return survey_question_page


class SurveyQuestionPageUpdate(graphene.Mutation):
    _name = 'SurveyQuestionPageUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = survey_question_page_type.SurveyQuestionPageUpdateInput(required=True)
        suggested_answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        conditional_questions = graphene.List(
            graphene.NonNull(survey_question_page_type.SurveyConditionalQuestionInput)
        )

    Output = survey_question_page_type.SurveyQuestionPage

    def mutate(self, info, id, input, suggested_answers=None, user_input_lines=None, conditional_questions=None):
        env = info.context["env"]

        update_suggested_answers = env['of.survey.question.answer']

        if suggested_answers:
            for suggested_answer in suggested_answers:
                if suggested_answer.id:
                    # on est sur une mise à jour
                    suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerUpdate().mutate(
                        info, id=suggested_answer.id, input=suggested_answer
                    )
                else:
                    suggested_answer = survey_question_answer_mutation.SurveyQuestionAnswerCreate().mutate(
                        info, input=suggested_answer
                    )
                update_suggested_answers += suggested_answer

        update_user_input_lines = env['of.survey.user_input.line']

        if user_input_lines:
            for user_input_line in user_input_lines:
                if user_input_line.id:
                    # on est sur une mise à jour
                    user_input_line = survey_user_input_line_mutation.SurveyUserInputLineUpdate().mutate(
                        info, id=user_input_line.id, input=user_input_line
                    )
                else:
                    user_input_line = survey_user_input_line_mutation.SurveyUserInputLineCreate().mutate(
                        info, input=user_input_line
                    )
                update_user_input_lines += user_input_line

        update_conditional_questions = env['of.survey.conditional.question']

        if conditional_questions:
            for conditional_question in conditional_questions:
                if conditional_question.id:
                    # on est sur une mise à jour
                    conditional_question = SurveyConditionalQuestionUpdate().mutate(
                        info, id=conditional_question.id, input=conditional_question
                    )
                else:
                    conditional_question = SurveyConditionalQuestionCreate().mutate(info, input=conditional_question)
                update_conditional_questions += conditional_question

        survey_question_page = lazy_update(env, 'of.survey.question', id, input)

        if update_suggested_answers:
            survey_question_page.suggested_answer_ids = [(6, 0, update_suggested_answers.ids)]

        if update_user_input_lines:
            survey_question_page.user_input_line_ids = [(6, 0, update_user_input_lines.ids)]

        if update_conditional_questions:
            survey_question_page.conditional_questions = [(6, 0, update_conditional_questions.ids)]

        return survey_question_page


class SurveyQuestionPageDelete(graphene.Mutation):
    _name = 'SurveyQuestionPageDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = survey_question_page_type.SurveyQuestionPage

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.survey.question', id)


class SurveyQuestionPageMutation(graphene.ObjectType):
    _name = 'SurveyQuestionPageMutation'
    _type = 'mutation'

    survey_question_page_create = SurveyQuestionPageCreate.Field()
    survey_question_page_update = SurveyQuestionPageUpdate.Field()
    survey_question_page_delete = SurveyQuestionPageDelete.Field()
