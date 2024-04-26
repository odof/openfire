import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from . import survey_question_page_type, survey_type, survey_user_input_type


class SurveyCreate(graphene.Mutation):
    _name = 'SurveyCreate'

    class Arguments:
        title = graphene.String()
        active = graphene.Boolean()
        question_pages = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))
        user_inputs = graphene.List(graphene.NonNull(survey_user_input_type.SurveyUserInputInput))

    Output = survey_type.Survey

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.survey.survey']._prepare_mutation_values(**args)
        return env['of.survey.survey'].create(values)


class SurveyUpdate(graphene.Mutation):
    _name = 'SurveyUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        title = graphene.String()
        active = graphene.Boolean()
        question_pages = graphene.List(graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput))
        user_inputs = graphene.List(graphene.NonNull(survey_user_input_type.SurveyUserInputInput))

    Output = survey_type.Survey

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.survey.survey']._prepare_mutation_values(**args)
        survey = env['of.survey.survey'].search([('id', '=', id)])
        return survey.write(values)


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
