# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .stock_move_type import StockMove


class StockMoveCreate(graphene.Mutation):
    _name = 'StockMoveCreate'

    class Arguments:
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)
        product = graphene.Argument(ProductInput)

    Output = StockMove

    def mutate(self, info, **args):
        env = info.context['env']
        values = env['stock.move']._prepare_mutation_values(**args)
        return env['stock.move'].create(values)


class StockMoveUpdate(graphene.Mutation):
    _name = 'StockMoveUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)
        product = graphene.Argument(ProductInput)

    Output = StockMove

    def mutate(self, info, id, **args):
        env = info.context['env']
        values = env['stock.move']._prepare_mutation_values(**args)
        move = env['stock.move'].search([('id', '=', id)])
        move.write(values)
        return move


class StockMoveDelete(graphene.Mutation):
    _name = 'StockMoveDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = StockMove

    def mutate(self, info, id):
        env = info.context['env']

        return lazy_delete(env, 'stock.move', id)


class StockMoveMutation(graphene.ObjectType):
    _name = 'StockMoveMutation'
    _type = 'mutation'

    stock_move_create = StockMoveCreate.Field()
    stock_move_update = StockMoveUpdate.Field()
    stock_move_delete = StockMoveDelete.Field()
