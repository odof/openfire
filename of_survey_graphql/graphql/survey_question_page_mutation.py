import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from . import survey_question_answer_type, survey_question_page_type, survey_user_input_line_type


class SurveyConditionalQuestionCreate(graphene.Mutation):
    _name = 'SurveyConditionalQuestionCreate'

    class Arguments:
        name = graphene.String()
        operator = graphene.String()
        question = graphene.Argument(survey_question_page_type.SurveyQuestionPageInput)
        triggering_question = graphene.Argument(survey_question_page_type.SurveyQuestionPageInput)
        answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))

    Output = survey_question_page_type.SurveyConditionalQuestion

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.survey.conditional.question']._prepare_mutation_values(**args)
        return env['of.survey.conditional.question'].create(values)


class SurveyConditionalQuestionUpdate(graphene.Mutation):
    _name = 'SurveyConditionalQuestionUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        operator = graphene.String()
        question = graphene.Argument(survey_question_page_type.SurveyQuestionPageInput)
        triggering_question = graphene.Argument(survey_question_page_type.SurveyQuestionPageInput)
        answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))

    Output = survey_question_page_type.SurveyConditionalQuestion

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.survey.conditional.question']._prepare_mutation_values(**args)
        conditional_question = env['of.survey.conditional.question'].search([('id', '=', id)])
        return conditional_question.write(values)


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
        title = graphene.String()
        sequence = graphene.Int()
        is_page = graphene.Boolean()
        question_type = graphene.String()
        is_conditional = graphene.Boolean()
        suggested_answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        conditional_questions = graphene.List(
            graphene.NonNull(survey_question_page_type.SurveyConditionalQuestionInput)
        )

    Output = survey_question_page_type.SurveyQuestionPage

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.survey.question']._prepare_mutation_values(**args)
        return env['of.survey.question'].create(values)


class SurveyQuestionPageUpdate(graphene.Mutation):
    _name = 'SurveyQuestionPageUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        title = graphene.String()
        sequence = graphene.Int()
        is_page = graphene.Boolean()
        question_type = graphene.String()
        is_conditional = graphene.Boolean()
        suggested_answers = graphene.List(graphene.NonNull(survey_question_answer_type.SurveyQuestionAnswerInput))
        user_input_lines = graphene.List(graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput))
        conditional_questions = graphene.List(
            graphene.NonNull(survey_question_page_type.SurveyConditionalQuestionInput)
        )

    Output = survey_question_page_type.SurveyQuestionPage

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.survey.question']._prepare_mutation_values(**args)
        question = env['of.survey.question'].search([('id', '=', id)])
        return question.write(values)


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
