# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .stock_lot_type import StockLot


class StockLotCreate(graphene.Mutation):
    _name = "StockLotCreate"

    class Arguments:
        name = graphene.String()

    Output = StockLot

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["stock.lot"]._prepare_mutation_values(**args)
        return env["stock.lot"].create(values)


class StockLotUpdate(graphene.Mutation):
    _name = "StockLotUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()

    Output = StockLot

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["stock.lot"]._prepare_mutation_values(**args)
        lot = env["stock.lot"].search([("id", "=", id)])
        lot.write(values)
        return lot


class StockLotDelete(graphene.Mutation):
    _name = "StockLotDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = StockLot

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "stock.lot", id)


class StockLotMutation(graphene.ObjectType):
    _name = "StockLotMutation"
    _type = "mutation"

    stock_lot_mutation_create = StockLotCreate.Field()
    stock_lot_mutation_update = StockLotUpdate.Field()
    stock_lot_mutation_delete = StockLotDelete.Field()
