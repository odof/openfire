# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from ..graphql.equipment_type import EquipmentInput
from .planning_intervention_equipment_link_type import PlanningInterventionEquipmentLink


class PlanningInterventionEquipmentLinkCreate(graphene.Mutation):
    _name = "PlanningInterventionEquipmentLinkCreate"

    class Arguments:
        name = graphene.String()
        equipment = graphene.Argument(EquipmentInput)

    Output = PlanningInterventionEquipmentLink

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["of.calendar.event.equipment.link"]._prepare_mutation_values(**args)
        return env["of.calendar.event.equipment.link"].create(values)


class PlanningInterventionEquipmentLinkUpdate(graphene.Mutation):
    _name = "PlanningInterventionEquipmentLinkUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        equipment = graphene.Argument(EquipmentInput)

    Output = PlanningInterventionEquipmentLink

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["of.calendar.event.equipment.link"]._prepare_mutation_values(**args)
        equipment = env["of.calendar.event.equipment.link"].search([("id", "=", id)])
        equipment.write(values)
        return equipment


class PlanningInterventionEquipmentLinkDelete(graphene.Mutation):
    _name = "PlanningInterventionEquipmentLinkDelete"

    class Arguments:
        id = graphene.Int()
        ids = graphene.List(graphene.NonNull(graphene.Int))

    Output = PlanningInterventionEquipmentLink

    def mutate(self, info, id, ids={}):
        env = info.context["env"]

        return lazy_delete(env, "of.calendar.event.equipment.link", id)


class PlanningInterventionEquipmentLinkMutation(graphene.ObjectType):
    _name = "PlanningInterventionEquipmentLinkMutation"
    _type = "mutation"

    planning_intervention_equipment_link_create = PlanningInterventionEquipmentLinkCreate.Field()
    planning_intervention_equipment_link_update = PlanningInterventionEquipmentLinkUpdate.Field()
    planning_intervention_equipment_link_delete = PlanningInterventionEquipmentLinkDelete.Field()
