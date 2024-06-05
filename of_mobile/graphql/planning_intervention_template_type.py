# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .planning_intervention_template_additional_line_type import (
    PlanningInterventionTemplateAdditionalLine,
    PlanningInterventionTemplateAdditionalLineInput,
)


class PlanningInterventionTemplate(OdooObjectType):
    _name = 'PlanningInterventionTemplate'
    _type = 'types'

    additional_line_ids = graphene.List(graphene.NonNull(PlanningInterventionTemplateAdditionalLine))
    send_reports = graphene.String(required=True)


class PlanningInterventionTemplateInput(graphene.InputObjectType):
    _name = 'PlanningInterventionTemplateInput'
    _type = 'types'

    additional_lines = graphene.List(graphene.NonNull(PlanningInterventionTemplateAdditionalLineInput))
    send_reports = graphene.Boolean()


class PlanningInterventionTemplateFilterInput(PlanningInterventionTemplateInput):
    _name = 'PlanningInterventionTemplateFilterInput'
