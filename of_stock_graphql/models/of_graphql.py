# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.picking_mutation import PickingMutation
from ..graphql.picking_query import PickingQuery
from ..graphql.picking_type import Picking, PickingCreateInput, PickingFilterInput, PickingUpdateInput
from ..graphql.stock_location_mutation import StockLocationMutation
from ..graphql.stock_location_query import StockLocationQuery
from ..graphql.stock_location_type import (
    StockLocation,
    StockLocationCreateInput,
    StockLocationFilterInput,
    StockLocationUpdateInput,
)
from ..graphql.stock_lot_mutation import StockLotMutation
from ..graphql.stock_lot_query import StockLotQuery
from ..graphql.stock_lot_type import StockLot, StockLotCreateInput, StockLotFilterInput, StockLotUpdateInput
from ..graphql.stock_move_mutation import StockMoveMutation
from ..graphql.stock_move_query import StockMoveQuery
from ..graphql.stock_move_type import StockMove, StockMoveCreateInput, StockMoveFilterInput, StockMoveUpdateInput
from ..graphql.stock_warehouse_mutation import StockWarehouseMutation
from ..graphql.stock_warehouse_query import StockWarehouseQuery
from ..graphql.stock_warehouse_type import (
    StockWarehouse,
    StockWarehouseCreateInput,
    StockWarehouseFilterInput,
    StockWarehouseUpdateInput,
)


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_stock_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Picking,
                PickingUpdateInput,
                PickingMutation,
                PickingQuery,
                PickingCreateInput,
                PickingFilterInput,
                StockMove,
                StockMoveUpdateInput,
                StockMoveMutation,
                StockMoveQuery,
                StockMoveFilterInput,
                StockMoveCreateInput,
                StockLocationQuery,
                StockLocation,
                StockLocationFilterInput,
                StockLocationUpdateInput,
                StockLocationCreateInput,
                StockLocationMutation,
                StockLotQuery,
                StockLot,
                StockLotFilterInput,
                StockLotUpdateInput,
                StockLotCreateInput,
                StockLotMutation,
                StockWarehouseQuery,
                StockWarehouse,
                StockWarehouseFilterInput,
                StockWarehouseUpdateInput,
                StockWarehouseCreateInput,
                StockWarehouseMutation,
            ],
        )
