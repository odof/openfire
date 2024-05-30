# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.picking_mutation import PickingMutation
from ..graphql.picking_query import PickingQuery
from ..graphql.picking_type import Picking, PickingFilterInput, PickingInput
from ..graphql.stock_location_mutation import StockLocationMutation
from ..graphql.stock_location_query import StockLocationQuery
from ..graphql.stock_location_type import StockLocation, StockLocationFilterInput, StockLocationInput
from ..graphql.stock_lot_mutation import StockLotMutation
from ..graphql.stock_lot_query import StockLotQuery
from ..graphql.stock_lot_type import StockLot, StockLotFilterInput, StockLotInput
from ..graphql.stock_move_mutation import StockMoveMutation
from ..graphql.stock_move_query import StockMoveQuery
from ..graphql.stock_move_type import StockMove, StockMoveFilterInput, StockMoveInput
from ..graphql.stock_warehouse_mutation import StockWarehouseMutation
from ..graphql.stock_warehouse_query import StockWarehouseQuery
from ..graphql.stock_warehouse_type import StockWarehouse, StockWarehouseFilterInput, StockWarehouseInput


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_stock_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Picking,
                PickingInput,
                PickingMutation,
                PickingQuery,
                PickingFilterInput,
                StockMove,
                StockMoveInput,
                StockMoveMutation,
                StockMoveQuery,
                StockMoveFilterInput,
                StockLocationQuery,
                StockLocation,
                StockLocationInput,
                StockLocationFilterInput,
                StockLocationMutation,
                StockLotQuery,
                StockLot,
                StockLotInput,
                StockLotFilterInput,
                StockLotMutation,
                StockWarehouseQuery,
                StockWarehouse,
                StockWarehouseInput,
                StockWarehouseFilterInput,
                StockWarehouseMutation,
            ],
        )
