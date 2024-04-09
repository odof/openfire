# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .stock_warehouse_type import StockWarehouse


class StockLocation(OdooObjectType):
    _name = 'StockLocation'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()
    warehouse = graphene.Field(StockWarehouse)

    @staticmethod
    def resolve_warehouse(root, info):
        return root.warehouse_id or None


class StockLocationInput(graphene.InputObjectType):
    _name = 'StockLocationInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()


class StockLocationFilterInput(StockLocationInput):
    _name = 'StockLocationFilterInput'


class StockLocationCreateInput(StockLocationInput):
    _name = 'StockLocationCreateInput'


class StockLocationUpdateInput(StockLocationInput):
    _name = 'StockLocationUpdateInput'
