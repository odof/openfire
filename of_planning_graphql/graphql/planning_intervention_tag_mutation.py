# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete
from odoo.addons.of_planning_graphql.graphql.planning_intervention_type import PlanningInterventionInput

from .planning_intervention_tag_type import PlanningInterventionTag


class PlanningInterventionTagCreate(graphene.Mutation):
    _name = "PlanningInterventionTagCreate"

    class Arguments:
        name = graphene.String()
        sequence = graphene.Int()
        active = graphene.Boolean()
        color = graphene.Int()
        interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))

    Output = PlanningInterventionTag

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["of.planning.tag"]._prepare_mutation_values(**args)
        return env["of.planning.tag"].create(values)


class PlanningInterventionTagUpdate(graphene.Mutation):
    _name = "PlanningInterventionTagUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        sequence = graphene.Int()
        active = graphene.Boolean()
        color = graphene.Int()
        interventions = graphene.List(graphene.NonNull(PlanningInterventionInput))

    Output = PlanningInterventionTag

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["of.planning.tag"]._prepare_mutation_values(**args)
        planning_tag = env["of.planning.tag"].search([("id", "=", id)])
        planning_tag.write(values)
        return planning_tag


class PlanningInterventionTagDelete(graphene.Mutation):
    _name = "PlanningInterventionTagDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = PlanningInterventionTag

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "of.planning.tag", id)


class PlanningInterventionTagMutation(graphene.ObjectType):
    _name = "PlanningInterventionTagMutation"
    _type = "mutation"

    planning_intervention_tag_create = PlanningInterventionTagCreate.Field()
    planning_intervention_tag_update = PlanningInterventionTagUpdate.Field()
    planning_intervention_tag_delete = PlanningInterventionTagDelete.Field()
