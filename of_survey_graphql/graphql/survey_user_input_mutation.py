import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from . import survey_question_page_type, survey_user_input_line_type, survey_user_input_type


class SurveyUserInputCreate(graphene.Mutation):
    _name = 'SurveyUserInputCreate'

    class Arguments:
        state = graphene.String()
        email = graphene.String()
        partner = graphene.Argument(PartnerInput)
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        predefined_questions = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))
        survey = graphene.Int(description="Id du survey")

    Output = survey_user_input_type.SurveyUserInput

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.survey.user_input']._prepare_mutation_values(**args)
        return env['of.survey.user_input'].create(values)


class SurveyUserInputUpdate(graphene.Mutation):
    _name = 'SurveyUserInputUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        state = graphene.String()
        email = graphene.String()
        partner = graphene.Argument(PartnerInput)
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        predefined_questions = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))
        survey = graphene.Int(description="Id du survey")

    Output = survey_user_input_type.SurveyUserInput

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.survey.user_input']._prepare_mutation_values(**args)
        user_input = env['of.survey.user_input'].search([('id', '=', id)])
        user_input.write(values)
        return user_input


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
