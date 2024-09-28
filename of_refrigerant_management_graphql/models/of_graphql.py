# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.fluid_type_query import FluidTypeQuery
from ..graphql.fluid_type_type import FluidType, FluidTypeInput
from ..graphql.recovery_cylinder_mutation import RecoveryCylinderMutation
from ..graphql.recovery_cylinder_query import RecoveryCylinderQuery
from ..graphql.recovery_cylinder_type import RecoveryCylinder, RecoveryCylinderInput


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_sale_management_template_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                FluidType,
                FluidTypeInput,
                FluidTypeQuery,
                RecoveryCylinder,
                RecoveryCylinderInput,
                RecoveryCylinderQuery,
                RecoveryCylinderMutation,
            ],
        )
