import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update
from odoo.addons.of_stock_graphql.graphql.stock_warehouse_mutation import StockWarehouseCreate, StockWarehouseUpdate

from .stock_location_type import StockLocation, StockLocationCreateInput, StockLocationUpdateInput
from .stock_warehouse_type import StockWarehouseInput


class StockLocationCreate(graphene.Mutation):
    _name = 'StockLocationCreate'

    class Arguments:
        input = StockLocationCreateInput(required=True)
        warehouse = StockWarehouseInput()

    Output = StockLocation

    def mutate(self, info, input, warehouse=None):
        env = info.context["env"]

        if warehouse:
            if warehouse.id:
                warehouse = StockWarehouseUpdate().mutate(info, id=warehouse.id, input=warehouse)
            else:
                warehouse = StockWarehouseCreate().mutate(info, input=warehouse)

        stock_location = lazy_create(env, 'stock.location', input)

        if warehouse:
            stock_location.warehouse_id = warehouse

        return stock_location


class StockLocationUpdate(graphene.Mutation):
    _name = 'StockLocationUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = StockLocationUpdateInput(required=True)
        warehouse = StockWarehouseInput()

    Output = StockLocation

    def mutate(self, info, id, input, warehouse=None):
        env = info.context["env"]

        if warehouse:
            if warehouse.id:
                warehouse = StockWarehouseUpdate().mutate(info, id=warehouse.id, input=warehouse)
            else:
                warehouse = StockWarehouseCreate().mutate(info, input=warehouse)

        stock_location = lazy_update(env, 'stock.location', id, input)

        if warehouse:
            stock_location.warehouse_id = warehouse

        return stock_location


class StockLocationDelete(graphene.Mutation):
    _name = 'StockLocationDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = StockLocation

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'stock.location', id)


class StockLocationMutation(graphene.ObjectType):
    _name = 'StockLocationMutation'
    _type = 'mutation'

    stock_location_create = StockLocationCreate.Field()
    stock_location_update = StockLocationUpdate.Field()
    stock_location_delete = StockLocationDelete.Field()
