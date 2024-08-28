# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.company_type import Company
from ..graphql.employee_type import Employee, EmployeeFilterInput
from ..graphql.image_type import Image, ImageInput
from ..graphql.planning_intervention_line_type import PlanningInterventionLine, PlanningInterventionLineInput
from ..graphql.planning_intervention_mutation import PlanningInterventionMutation
from ..graphql.planning_intervention_query import PlanningInterventionQuery
from ..graphql.planning_intervention_tag_mutation import PlanningInterventionTagMutation
from ..graphql.planning_intervention_tag_query import PlanningInterventionTagQuery
from ..graphql.planning_intervention_tag_type import (
    PlanningInterventionTag,
    PlanningInterventionTagFilterInput,
    PlanningInterventionTagInput,
)
from ..graphql.planning_intervention_task_mutation import PlanningInterventionTaskMutation
from ..graphql.planning_intervention_task_query import PlanningInterventionTaskQuery
from ..graphql.planning_intervention_task_type import (
    PlanningInterventionTask,
    PlanningInterventionTaskFilterInput,
    PlanningInterventionTaskInput,
)
from ..graphql.planning_intervention_template_mutation import PlanningInterventionTemplateMutation
from ..graphql.planning_intervention_template_query import PlanningInterventionTemplateQuery
from ..graphql.planning_intervention_template_type import (
    PlanningInterventionTemplate,
    PlanningInterventionTemplateFilterInput,
    PlanningInterventionTemplateInput,
)
from ..graphql.planning_intervention_type import (
    PlanningIntervention,
    PlanningInterventionFilterInput,
    PlanningInterventionInput,
)
from ..graphql.sale_order_type import SaleOrder


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_planning_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Employee,
                EmployeeFilterInput,
                Image,
                ImageInput,
                PlanningInterventionTaskQuery,
                PlanningInterventionTask,
                PlanningInterventionTaskInput,
                PlanningInterventionTaskFilterInput,
                PlanningInterventionTaskMutation,
                PlanningInterventionTemplateQuery,
                PlanningInterventionTemplate,
                PlanningInterventionTemplateMutation,
                PlanningInterventionTemplateFilterInput,
                PlanningInterventionTemplateInput,
                PlanningInterventionQuery,
                PlanningIntervention,
                PlanningInterventionInput,
                PlanningInterventionFilterInput,
                PlanningInterventionMutation,
                PlanningInterventionTagQuery,
                PlanningInterventionTag,
                PlanningInterventionTagInput,
                PlanningInterventionTagFilterInput,
                PlanningInterventionTagMutation,
                PlanningInterventionLine,
                PlanningInterventionLineInput,
                SaleOrder,
                Company,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            "ImageMutation": {
                "image_create": {
                    "intervention": PlanningInterventionInput,
                    "intervention_date": graphene.DateTime(),
                    "intervention_status": graphene.String(),
                },
                "image_update": {
                    "intervention": PlanningInterventionInput,
                    "intervention_date": graphene.DateTime(),
                    "intervention_status": graphene.String(),
                },
            },
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
