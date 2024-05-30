# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_survey_graphql.graphql.survey_type import Survey, SurveyInput


class PlanningInterventionTemplate(OdooObjectType):
    _name = 'PlanningInterventionTemplate'
    _type = 'types'

    survey_id = graphene.Field(Survey, name='survey')


class PlanningInterventionTemplateInput(graphene.InputObjectType):
    _name = "PlanningInterventionTemplateInput"
    _type = "types"

    survey = graphene.Field(SurveyInput)
