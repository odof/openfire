import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .stock_lot_type import StockLot, StockLotCreateInput, StockLotUpdateInput


class StockLotCreate(graphene.Mutation):
    _name = 'StockLotCreate'

    class Arguments:
        input = StockLotCreateInput(required=True)

    Output = StockLot

    def mutate(self, info, input):
        env = info.context["env"]

        stock_lot_mutation = lazy_create(env, 'stock.lot', input)

        return stock_lot_mutation


class StockLotUpdate(graphene.Mutation):
    _name = 'StockLotUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = StockLotUpdateInput(required=True)

    Output = StockLot

    def mutate(self, info, id, input):
        env = info.context["env"]

        stock_lot_mutation = lazy_update(env, 'stock.lot', id, input)

        return stock_lot_mutation


class StockLotDelete(graphene.Mutation):
    _name = 'StockLotDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = StockLot

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'stock.lot', id)


class StockLotMutation(graphene.ObjectType):
    _name = 'StockLotMutation'
    _type = 'mutation'

    stock_lot_mutation_create = StockLotCreate.Field()
    stock_lot_mutation_update = StockLotUpdate.Field()
    stock_lot_mutation_delete = StockLotDelete.Field()
