import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from . import survey_question_answer_type


class SurveyQuestionAnswerCreate(graphene.Mutation):
    _name = 'SurveyQuestionAnswerCreate'

    class Arguments:
        input = survey_question_answer_type.SurveyQuestionAnswerCreateInput(required=True)

    Output = survey_question_answer_type.SurveyQuestionAnswer

    def mutate(self, info, input):
        env = info.context["env"]

        survey_question_answer = lazy_create(env, 'of.survey.question.answer', input)

        return survey_question_answer


class SurveyQuestionAnswerUpdate(graphene.Mutation):
    _name = 'SurveyQuestionAnswerUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = survey_question_answer_type.SurveyQuestionAnswerUpdateInput(required=True)

    Output = survey_question_answer_type.SurveyQuestionAnswer

    def mutate(self, info, id, input, question=None):
        env = info.context["env"]

        survey_question_answer = lazy_update(env, 'of.survey.question.answer', id, input)

        return survey_question_answer


class SurveyQuestionAnswerDelete(graphene.Mutation):
    _name = 'SurveyQuestionAnswerDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = survey_question_answer_type.SurveyQuestionAnswer

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.survey.question.answer', id)


class SurveyQuestionAnswerMutation(graphene.ObjectType):
    _name = 'SurveyQuestionAnswerMutation'
    _type = 'mutation'

    survey_question_answer_create = SurveyQuestionAnswerCreate.Field()
    survey_question_answer_update = SurveyQuestionAnswerUpdate.Field()
    survey_question_answer_delete = SurveyQuestionAnswerDelete.Field()
