# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.fluid_nature_query import FluidNatureQuery
from ..graphql.fluid_nature_type import FluidNature, FluidNatureInput


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_industry_refrigerant_specialist_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                FluidNature,
                FluidNatureInput,
                FluidNatureQuery,
            ],
        )
