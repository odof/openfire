# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_planning_graphql.graphql.planning_intervention_task_type import (
    PlanningInterventionTask,
    PlanningInterventionTaskInput,
)


class EquipmentInterventionReportTemplate(OdooObjectType):
    _name = "EquipmentInterventionReportTemplate"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    task = graphene.Field(PlanningInterventionTask)

    @staticmethod
    def resolve_task(root, info):
        return root.task_id or None


class EquipmentInterventionReportTemplateInput(graphene.InputObjectType):
    _name = "EquipmentInterventionReportTemplateInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    task = graphene.Field(PlanningInterventionTaskInput)


class EquipmentInterventionReportTemplateFilterInput(EquipmentInterventionReportTemplateInput):
    _name = "EquipmentInterventionReportTemplateFilterInput"
