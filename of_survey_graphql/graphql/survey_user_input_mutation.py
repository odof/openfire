import graphene

from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from . import (
    survey_question_page_mutation,
    survey_question_page_type,
    survey_user_input_line_mutation,
    survey_user_input_line_type,
    survey_user_input_type,
)


class SurveyUserInputCreate(graphene.Mutation):
    _name = 'SurveyUserInputCreate'

    class Arguments:
        input = survey_user_input_type.SurveyUserInputCreateInput(required=True)
        partner = PartnerInput()
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        predefined_questions = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))

    Output = survey_user_input_type.SurveyUserInput

    def mutate(self, info, input, partner=None, user_input_lines=None, predefined_questions=None):
        env = info.context["env"]

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

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

        create_predefined_questions = env['of.survey.question']

        if predefined_questions:
            for predefined_question in predefined_questions:
                if predefined_questions.id:
                    # on est sur une mise à jour
                    predefined_question = survey_question_page_mutation.SurveyQuestionPageUpdate().mutate(
                        info, id=predefined_question.id, input=predefined_question
                    )
                else:
                    predefined_question = survey_question_page_mutation.SurveyQuestionPageCreate().mutate(
                        info, input=predefined_question
                    )
                create_predefined_questions += predefined_question

        survey_user_input = lazy_create(env, 'of.survey.user_input', input)

        if partner:
            survey_user_input.partner_id = partner

        if create_user_input_lines:
            survey_user_input.user_input_line_ids = [(6, 0, create_user_input_lines)]

        if create_predefined_questions:
            survey_user_input.predefined_question_ids = [(6, 0, create_predefined_questions)]

        return survey_user_input


class SurveyUserInputUpdate(graphene.Mutation):
    _name = 'SurveyUserInputUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = survey_user_input_type.SurveyUserInputUpdateInput(required=True)
        partner = PartnerInput()
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        predefined_questions = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))

    Output = survey_user_input_type.SurveyUserInput

    def mutate(self, info, id, input, partner=None, user_input_lines=None, predefined_questions=None):
        env = info.context["env"]

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

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

        update_predefined_questions = env['of.survey.question']

        if predefined_questions:
            for predefined_question in predefined_questions:
                if predefined_questions.id:
                    # on est sur une mise à jour
                    predefined_question = survey_question_page_mutation.SurveyQuestionPageUpdate().mutate(
                        info, id=predefined_question.id, input=predefined_question
                    )
                else:
                    predefined_question = survey_question_page_mutation.SurveyQuestionPageCreate().mutate(
                        info, input=predefined_question
                    )
                update_predefined_questions += predefined_question

        survey_user_input = lazy_update(env, 'of.survey.user_input', id, input)

        if partner:
            survey_user_input.partner_id = partner

        if update_user_input_lines:
            survey_user_input.user_input_line_ids = [(6, 0, update_user_input_lines)]

        if update_predefined_questions:
            survey_user_input.predefined_question_ids = [(6, 0, update_predefined_questions)]

        return survey_user_input


class SurveyUserInputDelete(graphene.Mutation):
    _name = 'SurveyUserInputDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = survey_user_input_type.SurveyUserInput

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.survey.user_input', id)


class SurveyUserInputMutation(graphene.ObjectType):
    _name = 'SurveyUserInputMutation'
    _type = 'mutation'

    survey_user_input_create = SurveyUserInputCreate.Field()
    survey_user_input_update = SurveyUserInputUpdate.Field()
    survey_user_input_delete = SurveyUserInputDelete.Field()
