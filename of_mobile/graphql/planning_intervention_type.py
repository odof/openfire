# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_equipment_graphql.graphql.equipment_type import Equipment


class PlanningIntervention(OdooObjectType):
    _name = 'PlanningIntervention'
    _type = 'types'

    update_date = graphene.DateTime()
    equipments = graphene.List(graphene.NonNull(Equipment))

    @staticmethod
    def resolve_update_date(root, info):
        return root.of_update_date or None

    @staticmethod
    def resolve_equipments(root, info):
        return root.of_equipment_ids or []


class PlanningInterventionsOffline(graphene.ObjectType):
    _name = 'PlanningInterventionsOffline'
    _type = 'types'

    interventions = graphene.List(
        graphene.NonNull(PlanningIntervention),
        required=True,
    )
    interventions_to_delete = graphene.List(
        graphene.NonNull(graphene.Int),
        required=True,
    )
