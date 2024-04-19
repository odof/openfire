# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.equipment_mutation import EquipmentMutation
from ..graphql.equipment_query import EquipmentQuery
from ..graphql.equipment_type import Equipment, EquipmentCreateInput, EquipmentFilterInput, EquipmentUpdateInput
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
                EquipmentCreateInput,
                EquipmentUpdateInput,
                EquipmentQuery,
                EquipmentMutation,
                PlanningIntervention,
            ],
        )
