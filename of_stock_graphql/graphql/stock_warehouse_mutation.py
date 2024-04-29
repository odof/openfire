import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .stock_warehouse_type import StockWarehouse


class StockWarehouseCreate(graphene.Mutation):
    _name = 'StockWarehouseCreate'

    class Arguments:
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)

    Output = StockWarehouse

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['stock.warehouse']._prepare_mutation_values(**args)
        return env['stock.warehouse'].create(values)


class StockWarehouseUpdate(graphene.Mutation):
    _name = 'StockWarehouseUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)

    Output = StockWarehouse

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['stock.warehouse']._prepare_mutation_values(**args)
        warehouse = env['stock.warehouse'].search([('id', '=', id)])
        warehouse.write(values)
        return warehouse


class StockWarehouseDelete(graphene.Mutation):
    _name = 'StockWarehouseDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = StockWarehouse

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'stock.warehouse', id)


class StockWarehouseMutation(graphene.ObjectType):
    _name = 'StockWarehouseMutation'
    _type = 'mutation'

    stock_warehouse_create = StockWarehouseCreate.Field()
    stock_warehouse_update = StockWarehouseUpdate.Field()
    stock_warehouse_delete = StockWarehouseDelete.Field()
