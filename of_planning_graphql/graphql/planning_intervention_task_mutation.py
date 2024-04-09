import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .planning_intervention_task_type import (
    PlanningInterventionTask,
    PlanningInterventionTaskCreateInput,
    PlanningInterventionTaskUpdateInput,
)


class PlanningInterventionTaskCreate(graphene.Mutation):
    _name = 'PlanningInterventionTaskCreate'

    class Arguments:
        input = PlanningInterventionTaskCreateInput(required=True)

    Output = PlanningInterventionTask

    def mutate(self, info, input):
        env = info.context["env"]

        return lazy_create(env, "of.planning.intervention", input)


class PlanningInterventionTaskUpdate(graphene.Mutation):
    _name = 'PlanningInterventionTaskUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PlanningInterventionTaskUpdateInput(required=True)

    Output = PlanningInterventionTask

    def mutate(self, info, id, input):
        env = info.context["env"]

        return lazy_update(env, "of.planning.intervention", id, input)


class PlanningInterventionTaskDelete(graphene.Mutation):
    _name = 'PlanningInterventionTaskDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningInterventionTask

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "of.planning.intervention", id)


class PlanningInterventionTaskMutation(graphene.ObjectType):
    _name = 'PlanningInterventionTaskMutation'
    _type = 'mutation'

    planning_intervention_task_create = PlanningInterventionTaskCreate.Field()
    planning_intervention_task_update = PlanningInterventionTaskUpdate.Field()
    planning_intervention_task_delete = PlanningInterventionTaskDelete.Field()
