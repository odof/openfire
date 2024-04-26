import graphene

from odoo.addons.of_base_graphql.graphql.product_type import ProductInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .account_move_line_type import AccountMoveLine


class AccountMoveLineCreate(graphene.Mutation):
    _name = 'AccountMoveLineCreate'

    class Arguments:
        name = graphene.String()
        quantity = graphene.Int()
        price_unit = graphene.Float()
        product = graphene.Argument(ProductInput)

    Output = AccountMoveLine

    def mutate(self, info, **args):
        env = info.context["env"]
        value = env['account.move.line']._prepare_mutation(**args)
        return env['account.move.line'].create(value)


class AccountMoveLineUpdate(graphene.Mutation):
    _name = 'AccountMoveLineUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        quantity = graphene.Int()
        price_unit = graphene.Float()
        product = graphene.Argument(ProductInput)

    Output = AccountMoveLine

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['account.move.line']._prepare_mutation_values(**args)
        move_lines = env['account.move.line'].search([('id', '=', id)])
        return move_lines.write(values)


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
