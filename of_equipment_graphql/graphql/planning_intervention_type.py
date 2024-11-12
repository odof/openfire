# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .equipment_type import Equipment, EquipmentInput
from .planning_intervention_equipment_link_type import (
    PlanningInterventionEquipmentLink,
    PlanningInterventionEquipmentLinkInput,
)


class PlanningIntervention(OdooObjectType):
    _name = "PlanningIntervention"
    _type = "types"

    of_equipment_ids = graphene.List(graphene.NonNull(Equipment), name="equipments")
    of_linked_equipment_ids = graphene.List(
        graphene.NonNull(PlanningInterventionEquipmentLink), name="linkedEquipments"
    )


class PlanningInterventionInput(graphene.InputObjectType):
    _name = "PlanningInterventionInput"
    _type = "types"

    equipments = graphene.List(graphene.NonNull(EquipmentInput))
    linked_equipments = graphene.List(graphene.NonNull(PlanningInterventionEquipmentLinkInput))
