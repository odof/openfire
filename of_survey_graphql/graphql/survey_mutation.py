import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from . import (
    survey_question_page_mutation,
    survey_question_page_type,
    survey_type,
    survey_user_input_mutation,
    survey_user_input_type,
)


class SurveyCreate(graphene.Mutation):
    _name = 'SurveyCreate'

    class Arguments:
        input = survey_type.SurveyCreateInput(required=True)
        question_pages = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))
        user_inputs = graphene.List(graphene.NonNull(survey_user_input_type.SurveyUserInputInput))

    Output = survey_type.Survey

    def mutate(self, info, input, question_pages=None, user_inputs=None):
        env = info.context["env"]

        create_question_pages = env['of.survey.question']

        if question_pages:
            for question_page in question_pages:
                if question_page.id:
                    # on est sur une mise à jour
                    question_page = survey_question_page_mutation.SurveyQuestionPageUpdate().mutate(
                        info, id=question_page.id, input=question_page
                    )
                else:
                    question_page = survey_question_page_mutation.SurveyQuestionPageCreate().mutate(
                        info, input=question_page
                    )
                create_question_pages += question_page

        create_user_inputs = env['of.survey.user_input']

        if user_inputs:
            for user_input in user_inputs:
                if user_input.id:
                    # on est sur une mise à jour
                    user_input = survey_user_input_mutation.SurveyUserInputUpdate().mutate(
                        info, id=user_input.id, input=user_input
                    )
                else:
                    user_input = survey_user_input_mutation.SurveyUserInputCreate().mutate(info, input=user_input)
                create_user_inputs += user_input

        survey = lazy_create(env, 'of.survey', input)

        if create_question_pages:
            survey.question_and_page_ids = [(6, 0, create_question_pages.ids)]

        if create_user_inputs:
            survey.user_input_ids = [(6, 0, create_user_inputs.ids)]

        return survey


class SurveyUpdate(graphene.Mutation):
    _name = 'SurveyUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = survey_type.SurveyUpdateInput(required=True)
        question_pages = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))
        user_inputs = graphene.List(graphene.NonNull(survey_user_input_type.SurveyUserInputInput))

    Output = survey_type.Survey

    def mutate(self, info, id, input, question_pages=None, user_inputs=None):
        env = info.context["env"]

        update_question_pages = env['of.survey.question']

        if question_pages:
            for question_page in question_pages:
                if question_page.id:
                    # on est sur une mise à jour
                    question_page = survey_question_page_mutation.SurveyQuestionPageUpdate().mutate(
                        info, id=question_page.id, input=question_page
                    )
                else:
                    question_page = survey_question_page_mutation.SurveyQuestionPageCreate().mutate(
                        info, input=question_page
                    )
                update_question_pages += question_page

        update_user_inputs = env['of.survey.user_input']

        if user_inputs:
            for user_input in user_inputs:
                if user_input.id:
                    # on est sur une mise à jour
                    user_input = survey_user_input_mutation.SurveyUserInputUpdate().mutate(
                        info, id=user_input.id, input=user_input
                    )
                else:
                    user_input = survey_user_input_mutation.SurveyUserInputCreate().mutate(info, input=user_input)
                update_user_inputs += user_input

        survey = lazy_update(env, 'of.survey', id, input)

        if update_question_pages:
            survey.question_and_page_ids = [(6, 0, update_question_pages.ids)]

        if update_user_inputs:
            survey.user_input_ids = [(6, 0, update_user_inputs.ids)]

        return survey


class SurveyDelete(graphene.Mutation):
    _name = 'SurveyDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = survey_type.Survey

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.survey', id)


class SurveyMutation(graphene.ObjectType):
    _name = 'SurveyMutation'
    _type = 'mutation'

    survey_create = SurveyCreate.Field()
    survey_update = SurveyUpdate.Field()
    survey_delete = SurveyDelete.Field()
