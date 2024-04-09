import graphene

from odoo.addons.of_account_graphql.graphql.account_fiscal_position_mutation import (
    AccountFiscalPositionCreate,
    AccountFiscalPositionUpdate,
)
from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import AccountFiscalPositionInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .planning_intervention_task_mutation import PlanningInterventionTaskCreate, PlanningInterventionTaskUpdate
from .planning_intervention_task_type import PlanningInterventionTaskInput
from .planning_intervention_template_type import (
    PlanningInterventionTemplate,
    PlanningInterventionTemplateCreateInput,
    PlanningInterventionTemplateUpdateInput,
)


class PlanningInterventionTemplateCreate(graphene.Mutation):
    _name = 'PlanningInterventionTemplateCreate'

    class Arguments:
        input = PlanningInterventionTemplateCreateInput(required=True)
        task = PlanningInterventionTaskInput()
        fiscal_position = AccountFiscalPositionInput()

    Output = PlanningInterventionTemplate

    def mutate(self, info, input, task=None, fiscal_position=None):
        env = info.context["env"]

        if task:
            if task.id:
                task = PlanningInterventionTaskUpdate().mutate(env, id=task.id, input=task)
            else:
                task = PlanningInterventionTaskCreate().mutate(env, input=task)

        if fiscal_position:
            if fiscal_position.id:
                fiscal_position = AccountFiscalPositionUpdate().mutate(
                    env, id=fiscal_position.id, input=fiscal_position
                )
            else:
                fiscal_position = AccountFiscalPositionCreate().mutate(env, input=fiscal_position)

        template = lazy_create(env, "of.planning.intervention.template", input)

        if task:
            template.task_id = task

        if fiscal_position:
            template.fiscal_position_id = fiscal_position

        return template


class PlanningInterventionTemplateUpdate(graphene.Mutation):
    _name = 'PlanningInterventionTemplateUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PlanningInterventionTemplateUpdateInput(required=True)
        task = PlanningInterventionTaskInput()
        fiscal_position = AccountFiscalPositionInput()

    Output = PlanningInterventionTemplate

    def mutate(self, info, id, input, task=None, fiscal_position=None):
        env = info.context["env"]

        if task:
            if task.id:
                task = PlanningInterventionTaskUpdate().mutate(env, id=task.id, input=task)
            else:
                task = PlanningInterventionTaskCreate().mutate(env, input=task)

        if fiscal_position:
            if fiscal_position.id:
                fiscal_position = AccountFiscalPositionUpdate().mutate(
                    env, id=fiscal_position.id, input=fiscal_position
                )
            else:
                fiscal_position = AccountFiscalPositionCreate().mutate(env, input=fiscal_position)

        template = lazy_update(env, "of.planning.intervention.template", id, input)

        if task:
            template.task_id = task

        if fiscal_position:
            template.fiscal_position_id = fiscal_position

        return template


class PlanningInterventionTemplateDelete(graphene.Mutation):
    _name = 'PlanningInterventionTemplateDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningInterventionTemplate

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "of.planning.intervention.template", id)


class PlanningInterventionTemplateMutation(graphene.ObjectType):
    _name = 'PlanningInterventionTemplateMutation'
    _type = 'mutation'

    planning_intervention_template_create = PlanningInterventionTemplateCreate.Field()
    planning_intervention_template_update = PlanningInterventionTemplateUpdate.Field()
    planning_intervention_template_delete = PlanningInterventionTemplateDelete.Field()
