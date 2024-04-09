# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner

from . import survey_question_page_type, survey_user_input_line_type


class SurveyUserInput(OdooObjectType):
    _name = 'SurveyUserInput'
    _type = 'types'

    id = graphene.Int(required=True)
    state = graphene.String()
    email = graphene.String()
    nickname = graphene.String()
    partner = graphene.Field(Partner)
    user_input_line_ids = graphene.List(
        graphene.NonNull(survey_user_input_line_type.SurveyUserInputLine), name="userInputLines"
    )
    predefined_question_ids = graphene.List(
        graphene.NonNull(survey_question_page_type.SurveyQuestionPage), name="predefinedQuestions"
    )

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None


class SurveyUserInputInput(graphene.InputObjectType):
    _name = 'SurveyUserInputInput'
    _type = 'types'

    id = graphene.Int()
    state = graphene.String()
    email = graphene.String()
    nickname = graphene.String()


class SurveyUserInputFilterInput(SurveyUserInputInput):
    _name = 'SurveyUserInputFilterInput'


class SurveyUserInputCreateInput(SurveyUserInputInput):
    _name = 'SurveyUserInputCreateInput'


class SurveyUserInputUpdateInput(SurveyUserInputInput):
    _name = 'SurveyUserInputUpdateInput'
