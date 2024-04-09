import graphene

from odoo.addons.of_base_graphql.graphql.product_mutation import ProductCreate, ProductUpdate
from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .account_move_line_type import AccountMoveLine, AccountMoveLineCreateInput, AccountMoveLineUpdateInput


class AccountMoveLineCreate(graphene.Mutation):
    _name = 'AccountMoveLineCreate'

    class Arguments:
        input = AccountMoveLineCreateInput(required=True)
        product = ProductInput()

    Output = AccountMoveLine

    def mutate(self, info, input, product=None):
        env = info.context["env"]

        if product:
            if product.id:
                product = ProductUpdate().mutate(info, id=product.id, input=product)
            else:
                product = ProductCreate().mutate(info, input=product)

        account_move_line = lazy_create(env, "account.move.line", input)

        if product:
            account_move_line.product_id = product

        return account_move_line


class AccountMoveLineUpdate(graphene.Mutation):
    _name = 'AccountMoveLineUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = AccountMoveLineUpdateInput(required=True)
        product = ProductInput()

    Output = AccountMoveLine

    def mutate(self, info, id, input, product=None):
        env = info.context["env"]

        if product:
            if product.id:
                product = ProductUpdate().mutate(info, id=product.id, input=product)
            else:
                product = ProductCreate().mutate(info, input=product)

        account_move_line = lazy_update(env, "account.move.line", id, input)

        if product:
            account_move_line.product_id = product

        return account_move_line


class AccountMoveLineDelete(graphene.Mutation):
    _name = 'AccountMoveLineDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = AccountMoveLine

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "account.move.line", id)


class AccountMoveLineMutation(graphene.ObjectType):
    _name = 'AccountMoveLineMutation'
    _type = 'mutation'

    account_move_line_create = AccountMoveLineCreate.Field()
    account_move_line_update = AccountMoveLineUpdate.Field()
    account_move_line_delete = AccountMoveLineDelete.Field()
