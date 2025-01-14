# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import graphene

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql
from odoo.addons.of_industry_graphql.graphql.technical_attribute_type import TechnicalAttributeInput

from ..graphql.equipment_type import Equipment, EquipmentInput


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_equipment_industry_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Equipment,
                EquipmentInput,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            "EquipmentMutation": {
                "equipment_create": {
                    "technical_attributes": graphene.List(graphene.NonNull(TechnicalAttributeInput)),
                },
                "equipment_update": {
                    "technical_attributes": graphene.List(graphene.NonNull(TechnicalAttributeInput)),
                },
            }
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
