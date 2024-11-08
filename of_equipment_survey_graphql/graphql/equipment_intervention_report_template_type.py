# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_survey_graphql.graphql.survey_type import Survey, SurveyInput


class EquipmentInterventionReportTemplate(OdooObjectType):
    _name = "EquipmentInterventionReportTemplate"
    _type = "types"

    survey = graphene.Field(Survey)

    @staticmethod
    def resolve_survey(root, info):
        return root.survey_id or None


class EquipmentInterventionReportTemplateInput(graphene.InputObjectType):
    _name = "EquipmentInterventionReportTemplateInput"
    _type = "types"

    survey = graphene.Field(SurveyInput)
