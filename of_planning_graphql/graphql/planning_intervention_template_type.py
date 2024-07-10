# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import (
    AccountFiscalPosition,
    AccountFiscalPositionInput,
)

from .planning_intervention_task_type import PlanningInterventionTask, PlanningInterventionTaskInput


class PlanningInterventionTemplate(OdooObjectType):
    _name = 'PlanningInterventionTemplate'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    is_default_template = graphene.Boolean(required=True)
    task = graphene.Field(PlanningInterventionTask)
    fiscal_position = graphene.Field(AccountFiscalPosition)

    def resolve_task(root, info):
        return root.task_id or None

    def resolve_fiscal_position(root, info):
        return root.fiscal_position_id or None


class PlanningInterventionTemplateInput(graphene.InputObjectType):
    _name = 'PlanningInterventionTemplateInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    is_default_template = graphene.Boolean()
    task = graphene.Field(PlanningInterventionTaskInput)
    fiscal_position = graphene.Field(AccountFiscalPositionInput)


class PlanningInterventionTemplateFilterInput(PlanningInterventionTemplateInput):
    _name = 'PlanningInterventionTemplateFilterInput'
