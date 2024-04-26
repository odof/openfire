import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .planning_intervention_task_type import PlanningInterventionTask


class PlanningInterventionTaskCreate(graphene.Mutation):
    _name = 'PlanningInterventionTaskCreate'

    class Arguments:
        name = graphene.String()
        description = graphene.String(default_value="")
        duration = graphene.Float()

    Output = PlanningInterventionTask

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['of.planning.task']._prepare_mutation_values(**args)
        return env['of.planning.task'].create(values)


class PlanningInterventionTaskUpdate(graphene.Mutation):
    _name = 'PlanningInterventionTaskUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        description = graphene.String(default_value="")
        duration = graphene.Float()

    Output = PlanningInterventionTask

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['of.planning.task']._prepare_mutation_values(**args)
        task = env['of.planning.task'].search([('id', '=', id)])
        return task.write(values)


class PlanningInterventionTaskDelete(graphene.Mutation):
    _name = 'PlanningInterventionTaskDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningInterventionTask

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "of.planning.task", id)


class PlanningInterventionTaskMutation(graphene.ObjectType):
    _name = 'PlanningInterventionTaskMutation'
    _type = 'mutation'

    planning_intervention_task_create = PlanningInterventionTaskCreate.Field()
    planning_intervention_task_update = PlanningInterventionTaskUpdate.Field()
    planning_intervention_task_delete = PlanningInterventionTaskDelete.Field()
