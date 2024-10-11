# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_base_graphql.graphql.image_type import ImageInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from . import survey_question_answer_type, survey_question_page_type, survey_user_input_line_type


class SurveyUserInputLineCreate(graphene.Mutation):
    _name = "SurveyUserInputLineCreate"

    class Arguments:
        skipped = graphene.Boolean()
        answer_type = graphene.String()
        value_char_box = graphene.String()
        value_date = graphene.Date()
        value_text_box = graphene.String()
        value_numerical_box = graphene.Float()
        suggested_answer = graphene.Argument(survey_question_answer_type.SurveyQuestionAnswerInput)
        question = graphene.Argument(survey_question_page_type.SurveyQuestionPageInput)
        images = graphene.List(graphene.NonNull(ImageInput))
        comment = graphene.String()

    Output = survey_user_input_line_type.SurveyUserInputLine

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["of.survey.user_input.line"]._prepare_mutation_values(**args)
        return env["of.survey.user_input.line"].create(values)


class SurveyUserInputLineUpdate(graphene.Mutation):
    _name = "SurveyUserInputLineUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        skipped = graphene.Boolean()
        answer_type = graphene.String()
        value_char_box = graphene.String()
        value_date = graphene.Date()
        value_text_box = graphene.String()
        value_numerical_box = graphene.Float()
        suggested_answer = graphene.Argument(survey_question_answer_type.SurveyQuestionAnswerInput)
        question = graphene.Argument(survey_question_page_type.SurveyQuestionPageInput)
        images = graphene.List(graphene.NonNull(ImageInput))
        comment = graphene.String()

    Output = survey_user_input_line_type.SurveyUserInputLine

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["of.survey.user_input.line"]._prepare_mutation_values(**args)
        user_input_line = env["of.survey.user_input.line"].search([("id", "=", id)])
        user_input_line.write(values)
        return user_input_line


class SurveyUserInputLineDelete(graphene.Mutation):
    _name = "SurveyUserInputLineDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = survey_user_input_line_type.SurveyUserInputLine

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "of.survey.user_input.line", id)


class SurveyUserInputLineMutation(graphene.ObjectType):
    _name = "SurveyUserInputLineMutation"
    _type = "mutation"

    survey_user_input_line_create = SurveyUserInputLineCreate.Field()
    survey_user_input_line_update = SurveyUserInputLineUpdate.Field()
    survey_user_input_line_delete = SurveyUserInputLineDelete.Field()
