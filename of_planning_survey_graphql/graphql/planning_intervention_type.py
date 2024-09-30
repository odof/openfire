# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_survey_graphql.graphql.survey_type import Survey
from odoo.addons.of_survey_graphql.graphql.survey_user_input_type import SurveyUserInput


class PlanningIntervention(OdooObjectType):
    _name = "PlanningIntervention"
    _type = "types"

    survey = graphene.Field(Survey)
    survey_user_input = graphene.Field(SurveyUserInput)

    def resolve_survey(root, info):
        return root.of_survey_id or None

    def resolve_survey_user_input(root, info):
        return root.of_survey_user_input_id or None
