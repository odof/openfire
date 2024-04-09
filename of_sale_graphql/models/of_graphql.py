# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.sale_order_line_mutation import SaleOrderLineMutation
from ..graphql.sale_order_line_query import SaleOrderLineQuery
from ..graphql.sale_order_line_type import (
    SaleOrderLine,
    SaleOrderLineCreateInput,
    SaleOrderLineFilterInput,
    SaleOrderLineUpdateInput,
)
from ..graphql.sale_order_mutation import SaleOrderMutation
from ..graphql.sale_order_query import SaleOrderQuery
from ..graphql.sale_order_type import SaleOrder, SaleOrderCreateInput, SaleOrderFilterInput, SaleOrderUpdateInput


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_sale_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                SaleOrder,
                SaleOrderUpdateInput,
                SaleOrderLine,
                SaleOrderLineUpdateInput,
                SaleOrderQuery,
                SaleOrderLineQuery,
                SaleOrderLineCreateInput,
                SaleOrderLineFilterInput,
                SaleOrderFilterInput,
                SaleOrderCreateInput,
                SaleOrderMutation,
                SaleOrderLineMutation,
            ],
        )
