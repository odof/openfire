# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .equipment_type import Equipment


class PlanningIntervention(OdooObjectType):
    _name = "PlanningIntervention"
    _type = "types"

    of_equipment_ids = graphene.List(graphene.NonNull(Equipment), name="equipments")
