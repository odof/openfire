# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_survey_graphql.graphql.survey_type import Survey, SurveyInput
from odoo.addons.of_survey_graphql.graphql.survey_user_input_type import SurveyUserInput, SurveyUserInputInput


class PlanningInterventionEquipmentLink(OdooObjectType):
    _name = "PlanningInterventionEquipmentLink"
    _type = "types"

    survey = graphene.Field(Survey)

    survey_user_input = graphene.Field(SurveyUserInput)

    @staticmethod
    def resolve_survey(root, info):
        return root.survey_id or None

    @staticmethod
    def resolve_survey_user_input(root, info):
        return root.survey_user_input_id or None


class PlanningInterventionEquipmentLinkInput(graphene.InputObjectType):
    _name = "PlanningInterventionEquipmentLinkInput"
    _type = "types"

    survey = graphene.Field(SurveyInput)

    survey_user_input = graphene.Field(SurveyUserInputInput)
