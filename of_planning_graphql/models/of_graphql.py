# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.employee_type import Employee, EmployeeFilterInput
from ..graphql.planning_intervention_line_type import PlanningInterventionLine
from ..graphql.planning_intervention_mutation import PlanningInterventionMutation
from ..graphql.planning_intervention_query import PlanningInterventionQuery
from ..graphql.planning_intervention_tag_mutation import PlanningInterventionTagMutation
from ..graphql.planning_intervention_tag_query import PlanningInterventionTagQuery
from ..graphql.planning_intervention_tag_type import (
    PlanningInterventionTag,
    PlanningInterventionTagCreateInput,
    PlanningInterventionTagFilterInput,
    PlanningInterventionTagUpdateInput,
)
from ..graphql.planning_intervention_task_mutation import PlanningInterventionTaskMutation
from ..graphql.planning_intervention_task_query import PlanningInterventionTaskQuery
from ..graphql.planning_intervention_task_type import (
    PlanningInterventionTask,
    PlanningInterventionTaskCreateInput,
    PlanningInterventionTaskFilterInput,
    PlanningInterventionTaskUpdateInput,
)
from ..graphql.planning_intervention_template_mutation import PlanningInterventionTemplateMutation
from ..graphql.planning_intervention_template_query import PlanningInterventionTemplateQuery
from ..graphql.planning_intervention_template_type import (
    PlanningInterventionTemplate,
    PlanningInterventionTemplateCreateInput,
    PlanningInterventionTemplateFilterInput,
    PlanningInterventionTemplateUpdateInput,
)
from ..graphql.planning_intervention_type import (
    PlanningIntervention,
    PlanningInterventionCreateInput,
    PlanningInterventionFilterInput,
    PlanningInterventionUpdateInput,
)


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_planning_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Employee,
                EmployeeFilterInput,
                PlanningInterventionTaskQuery,
                PlanningInterventionTask,
                PlanningInterventionTaskFilterInput,
                PlanningInterventionTaskCreateInput,
                PlanningInterventionTaskUpdateInput,
                PlanningInterventionTaskMutation,
                PlanningInterventionTemplateQuery,
                PlanningInterventionTemplate,
                PlanningInterventionTemplateCreateInput,
                PlanningInterventionTemplateUpdateInput,
                PlanningInterventionTemplateMutation,
                PlanningInterventionTemplateFilterInput,
                PlanningInterventionQuery,
                PlanningInterventionCreateInput,
                PlanningIntervention,
                PlanningInterventionFilterInput,
                PlanningInterventionUpdateInput,
                PlanningInterventionMutation,
                PlanningInterventionTagQuery,
                PlanningInterventionTag,
                PlanningInterventionTagFilterInput,
                PlanningInterventionTagUpdateInput,
                PlanningInterventionTagCreateInput,
                PlanningInterventionTagMutation,
                PlanningInterventionLine,
            ],
        )
