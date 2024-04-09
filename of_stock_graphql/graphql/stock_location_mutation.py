# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .stock_location_type import StockLocation
from .stock_warehouse_type import StockWarehouseInput


class StockLocationCreate(graphene.Mutation):
    _name = 'StockLocationCreate'

    class Arguments:
        name = graphene.String()
        warehouse = graphene.Argument(StockWarehouseInput)

    Output = StockLocation

    def mutate(self, info, **args):
        env = info.context['env']
        values = env['stock.location']._prepare_mutation_values(**args)
        return env['stock.location'].create(values)


class StockLocationUpdate(graphene.Mutation):
    _name = 'StockLocationUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        warehouse = graphene.Argument(StockWarehouseInput)

    Output = StockLocation

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['stock.location']._prepare_mutation_values(**args)
        location = env['stock.location'].search([('id', '=', id)])
        location.write(values)
        return location


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
