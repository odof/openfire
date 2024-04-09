# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from . import survey_question_answer_type


class SurveyQuestionAnswerCreate(graphene.Mutation):
    _name = 'SurveyQuestionAnswerCreate'

    class Arguments:
        value = graphene.String()
        sequence = graphene.Int()
        is_correct = graphene.Boolean()
        is_default = graphene.Boolean()

    Output = survey_question_answer_type.SurveyQuestionAnswer

    def mutate(self, info, **args):
        env = info.context['env']
        values = env['of.survey.question.answer']._prepare_mutation_values(**args)
        return env['of.survey.question.answer'].create(values)


class SurveyQuestionAnswerUpdate(graphene.Mutation):
    _name = 'SurveyQuestionAnswerUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        value = graphene.String()
        sequence = graphene.Int()
        is_correct = graphene.Boolean()
        is_default = graphene.Boolean()

    Output = survey_question_answer_type.SurveyQuestionAnswer

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['of.survey.question.answer']._prepare_mutation_values(**args)
        answer = env['of.survey.question.answer'].search([('id', '=', id)])
        answer.write(values)
        return answer


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
