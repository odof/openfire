import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update
from odoo.addons.of_planning_graphql.graphql.planning_intervention_mutation import (
    PlanningInterventionCreate,
    PlanningInterventionUpdate,
)
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningInterventionInput

from .planning_intervention_tag_type import (
    PlanningInterventionTag,
    PlanningInterventionTagCreateInput,
    PlanningInterventionTagUpdateInput,
)


class PlanningInterventionTagCreate(graphene.Mutation):
    _name = 'PlanningInterventionTagCreate'

    class Arguments:
        input = PlanningInterventionTagCreateInput(required=True)
        interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))

    Output = PlanningInterventionTag

    def mutate(self, info, input, interventions=None):
        env = info.context["env"]

        create_interventions = env['of.planning.intervention']

        if interventions:
            for intervention in interventions:
                if intervention.id:
                    # on est sur une mise à jour
                    intervention = PlanningInterventionUpdate().mutate(info, id=intervention.id, input=intervention)
                else:
                    intervention = PlanningInterventionCreate().mutate(info, input=intervention)
                create_interventions += intervention

        planning_intervention_tag = lazy_create(env, 'of.planning.tag', input)

        if create_interventions:
            planning_intervention_tag.intervention_ids = [(6, 0, create_interventions.ids)]

        return planning_intervention_tag


class PlanningInterventionTagUpdate(graphene.Mutation):
    _name = 'PlanningInterventionTagUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = PlanningInterventionTagUpdateInput(required=True)
        interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))

    Output = PlanningInterventionTag

    def mutate(self, info, id, input, interventions=None):
        env = info.context["env"]

        update_interventions = env['of.planning.intervention']

        if interventions:
            for intervention in interventions:
                if intervention.id:
                    # on est sur une mise à jour
                    intervention = PlanningInterventionUpdate().mutate(info, id=intervention.id, input=intervention)
                else:
                    intervention = PlanningInterventionCreate().mutate(info, input=intervention)
                update_interventions += intervention

        planning_intervention_tag = lazy_update(env, 'of.planning.tag', id, input)

        if update_interventions:
            planning_intervention_tag.intervention_ids = [(6, 0, update_interventions.ids)]

        return planning_intervention_tag


class PlanningInterventionTagDelete(graphene.Mutation):
    _name = 'PlanningInterventionTagDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningInterventionTag

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.planning.tag', id)


class PlanningInterventionTagMutation(graphene.ObjectType):
    _name = 'PlanningInterventionTagMutation'
    _type = 'mutation'

    planning_intervention_tag_create = PlanningInterventionTagCreate.Field()
    planning_intervention_tag_update = PlanningInterventionTagUpdate.Field()
    planning_intervention_tag_delete = PlanningInterventionTagDelete.Field()
