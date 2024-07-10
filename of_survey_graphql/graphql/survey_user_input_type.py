# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput

from . import survey_question_page_type, survey_user_input_line_type


class SurveyUserInput(OdooObjectType):
    _name = 'SurveyUserInput'
    _type = 'types'

    id = graphene.Int(required=True)
    state = graphene.String()
    email = graphene.String()
    partner = graphene.Field(Partner)
    user_input_line_ids = graphene.List(
        graphene.NonNull(survey_user_input_line_type.SurveyUserInputLine), name="userInputLines"
    )
    predefined_question_ids = graphene.List(
        graphene.NonNull(survey_question_page_type.SurveyQuestionPage), name="predefinedQuestions"
    )
    survey = graphene.Int(description="Id du survey")

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None

    @staticmethod
    def resolve_survey(root, info):
        return root.survey_id or None


class SurveyUserInputInput(graphene.InputObjectType):
    _name = 'SurveyUserInputInput'
    _type = 'types'

    id = graphene.Int()
    state = graphene.String()
    email = graphene.String()
    partner = graphene.Field(PartnerInput)
    user_input_lines = graphene.List(
        graphene.NonNull(survey_user_input_line_type.SurveyUserInputLineInput),
    )
    predefined_questions = graphene.List(
        graphene.NonNull(survey_question_page_type.SurveyQuestionPageInput),
    )
    survey = graphene.Int(description="Id du survey")


class SurveyUserInputFilterInput(SurveyUserInputInput):
    _name = 'SurveyUserInputFilterInput'
