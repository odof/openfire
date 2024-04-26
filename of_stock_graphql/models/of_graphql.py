# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.picking_mutation import PickingMutation
from ..graphql.picking_query import PickingQuery
from ..graphql.picking_type import Picking, PickingFilterInput
from ..graphql.stock_location_mutation import StockLocationMutation
from ..graphql.stock_location_query import StockLocationQuery
from ..graphql.stock_location_type import StockLocation, StockLocationFilterInput
from ..graphql.stock_lot_mutation import StockLotMutation
from ..graphql.stock_lot_query import StockLotQuery
from ..graphql.stock_lot_type import StockLot, StockLotFilterInput
from ..graphql.stock_move_mutation import StockMoveMutation
from ..graphql.stock_move_query import StockMoveQuery
from ..graphql.stock_move_type import StockMove, StockMoveFilterInput
from ..graphql.stock_warehouse_mutation import StockWarehouseMutation
from ..graphql.stock_warehouse_query import StockWarehouseQuery
from ..graphql.stock_warehouse_type import StockWarehouse, StockWarehouseFilterInput


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_stock_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Picking,
                PickingMutation,
                PickingQuery,
                PickingFilterInput,
                StockMove,
                StockMoveMutation,
                StockMoveQuery,
                StockMoveFilterInput,
                StockLocationQuery,
                StockLocation,
                StockLocationFilterInput,
                StockLocationMutation,
                StockLotQuery,
                StockLot,
                StockLotFilterInput,
                StockLotMutation,
                StockWarehouseQuery,
                StockWarehouse,
                StockWarehouseFilterInput,
                StockWarehouseMutation,
            ],
        )
