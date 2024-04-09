import graphene

from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_base_graphql.graphql.product_mutation import ProductCreate, ProductUpdate
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .stock_move_type import StockMove, StockMoveCreateInput, StockMoveUpdateInput


class StockMoveCreate(graphene.Mutation):
    _name = 'StockMoveCreate'

    class Arguments:
        input = StockMoveCreateInput(required=True)
        partner = PartnerInput()
        product = ProductInput()

    Output = StockMove

    def mutate(self, info, input, partner=None, product=None):
        env = info.context["env"]

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if product:
            if product.id:
                product = ProductUpdate().mutate(info, id=product.id, input=product)
            else:
                product = ProductCreate().mutate(info, input=product)

        stock_move = lazy_create(env, "stock.move", input)

        if partner:
            stock_move.partner_id = partner

        if product:
            stock_move.product_id = product

        return stock_move


class StockMoveUpdate(graphene.Mutation):
    _name = 'StockMoveUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = StockMoveUpdateInput(required=True)
        partner = PartnerInput()
        product = ProductInput()

    Output = StockMove

    def mutate(self, info, id, input, partner=None, product=None):
        env = info.context["env"]

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if product:
            if product.id:
                product = ProductUpdate().mutate(info, id=product.id, input=product)
            else:
                product = ProductCreate().mutate(info, input=product)

        stock_move = lazy_update(env, "stock.move", id, input)

        if partner:
            stock_move.partner_id = partner

        if product:
            stock_move.product_id = product

        return stock_move


class StockMoveDelete(graphene.Mutation):
    _name = 'StockMoveDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = StockMove

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "stock.move", id)


class StockMoveMutation(graphene.ObjectType):
    _name = 'StockMoveMutation'
    _type = 'mutation'

    stock_move_create = StockMoveCreate.Field()
    stock_move_update = StockMoveUpdate.Field()
    stock_move_delete = StockMoveDelete.Field()
