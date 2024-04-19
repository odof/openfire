import graphene

from odoo.addons.of_planning_graphql.graphql.planning_intervention_mutation import (
    PlanningInterventionCreate,
    PlanningInterventionUpdate,
)

from .equipment_mutation import EquipmentCreate, EquipmentUpdate
from .equipment_type import EquipmentInput


class PlanningInterventionCreateEquipments(PlanningInterventionCreate):
    _name = 'PlanningInterventionCreate'

    class Arguments(PlanningInterventionCreate.Arguments):
        equipments = graphene.List(graphene.NonNull(EquipmentInput))

    def mutate(self, info, input, **args):
        env = info.context["env"]
        create_equipments = env['of.equipment']
        equipments = []

        if args.get('equipments', False):
            equipments = args.pop('equipments')

        intervention = PlanningInterventionCreate.mutate(self, info, input, **args)

        for equipment in equipments:
            if equipment.id:
                equipment = EquipmentUpdate().mutate(info, id=equipment.id, input=equipment)
            else:
                equipment = EquipmentCreate().mutate(info, input=equipment)

            create_equipments += equipment

        if len(create_equipments) > 0:
            intervention.of_equipment_ids = [(6, 0, create_equipments.ids)]
            intervention.of_use_equipment = True

        return intervention


class PlanningInterventionUpdateEquipments(PlanningInterventionUpdate):
    _name = 'PlanningInterventionUpdate'

    class Arguments(PlanningInterventionUpdate.Arguments):
        equipments = graphene.List(graphene.NonNull(EquipmentInput))

    def mutate(self, info, input, **args):
        env = info.context["env"]
        update_equipments = env['of.equipment']
        equipments = []

        if args.get('equipments', False):
            equipments = args.pop('equipments')

        intervention = PlanningInterventionUpdate.mutate(self, info, input, **args)

        for equipment in equipments:
            if equipment.id:
                equipment = EquipmentUpdate().mutate(info, id=equipment.id, input=equipment)
            else:
                equipment = EquipmentCreate().mutate(info, input=equipment)

            update_equipments += equipment

        if len(update_equipments) > 0:
            intervention.of_equipment_ids = [(6, 0, update_equipments.ids)]
            intervention.of_use_equipment = True

        return intervention


class PlanningInterventionMutation(graphene.ObjectType):
    _name = 'PlanningInterventionMutation'
    _type = 'mutation'

    planning_intervention_update = PlanningInterventionUpdateEquipments.Field()
    planning_intervention_create = PlanningInterventionCreateEquipments.Field()
