# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo import models

from odoo.addons.of_equipment_graphql.graphql.equipment_type import EquipmentInput
from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.equipment_mutation import EquipmentMutation
from ..graphql.equipment_query import EquipmentQuery
from ..graphql.equipment_type import Equipment, EquipmentFilterInput
from ..graphql.planning_intervention_type import PlanningIntervention


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_equipment_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Equipment,
                EquipmentFilterInput,
                EquipmentQuery,
                EquipmentMutation,
                PlanningIntervention,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            "PlanningInterventionMutation": {
                "planning_intervention_create": {
                    "equipments": graphene.List(graphene.NonNull(EquipmentInput)),
                },
                "planning_intervention_update": {
                    "equipments": graphene.List(graphene.NonNull(EquipmentInput)),
                },
            }
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
