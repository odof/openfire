# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import AccountFiscalPosition

from .planning_intervention_task_type import PlanningInterventionTask


class PlanningInterventionTemplate(OdooObjectType):
    _name = "PlanningInterventionTemplate"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    is_default_template = graphene.Boolean(required=True)
    task_id = graphene.Field(PlanningInterventionTask, name='task')
    fiscal_position_id = graphene.Field(AccountFiscalPosition, name='fiscalPosition')


class PlanningInterventionTemplateInput(graphene.InputObjectType):
    _name = "PlanningInterventionTemplateInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    is_default_template = graphene.Boolean()


class PlanningInterventionTemplateFilterInput(PlanningInterventionTemplateInput):
    _name = "PlanningInterventionTemplateFilterInput"


class PlanningInterventionTemplateCreateInput(PlanningInterventionTemplateInput):
    _name = "PlanningInterventionTemplateCreateInput"


class PlanningInterventionTemplateUpdateInput(PlanningInterventionTemplateInput):
    _name = "PlanningInterventionTemplateUpdateInput"
