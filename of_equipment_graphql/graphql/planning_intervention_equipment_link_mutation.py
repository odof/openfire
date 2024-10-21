# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.delete_result_type import DeleteResult
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete_ids

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
        return env["of.calendar.event.equipment.link"].with_context(of_ignore_event_state=True).create(values)


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
        equipment.with_context(of_ignore_event_state=True).write(values)
        return equipment


class PlanningInterventionEquipmentLinkDelete(graphene.Mutation):
    _name = "PlanningInterventionEquipmentLinkDelete"

    class Arguments:
        ids = graphene.List(graphene.NonNull(graphene.Int), required=True)

    Output = DeleteResult

    def mutate(self, info, ids):
        env = info.context["env"]

        deleted_ids = lazy_delete_ids(
            env, "of.calendar.event.equipment.link", ids, context={"of_ignore_event_state": True}
        )
        non_existent_ids = list(set(ids) - set(deleted_ids))
        return DeleteResult(deleted_ids=deleted_ids, non_existent_ids=non_existent_ids)


class PlanningInterventionEquipmentLinkMutation(graphene.ObjectType):
    _name = "PlanningInterventionEquipmentLinkMutation"
    _type = "mutation"

    planning_intervention_equipment_link_create = PlanningInterventionEquipmentLinkCreate.Field()
    planning_intervention_equipment_link_update = PlanningInterventionEquipmentLinkUpdate.Field()
    planning_intervention_equipment_link_delete = PlanningInterventionEquipmentLinkDelete.Field()
