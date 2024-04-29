import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .account_fiscal_position_type import AccountFiscalPositionInput
from .account_move_line_type import AccountMoveLineInput
from .account_move_type import AccountMove


class AccountMoveCreate(graphene.Mutation):
    _name = 'AccountMoveCreate'

    class Arguments:
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)
        lines = graphene.Argument(AccountMoveLineInput)
        fiscal_position = graphene.Argument(AccountFiscalPositionInput)

    Output = AccountMove

    def mutate(self, info, **args):
        env = info.context["env"]
        value = env['account.move']._prepare_mutation(**args)
        return env['account.move'].create(value)


class AccountMoveUpdate(graphene.Mutation):
    _name = 'AccountMoveUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        partner = graphene.Argument(PartnerInput)
        lines = graphene.Argument(AccountMoveLineInput)
        fiscal_position = graphene.Argument(AccountFiscalPositionInput)

    Output = AccountMove

    def mutate(self, info, id, **args):
        env = info.context["env"]
        value = env['account.move']._prepare_mutation(**args)
        account_move = env['account.move'].search([('id', '=', id)])
        account_move.write(value)
        return account_move


class AccountMoveDelete(graphene.Mutation):
    _name = 'AccountMoveDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = AccountMove

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "account.move", id)


class AccountMoveMutation(graphene.ObjectType):
    _name = 'AccountMoveMutation'
    _type = 'mutation'

    account_move_create = AccountMoveCreate.Field()
    account_move_update = AccountMoveUpdate.Field()
    account_move_delete = AccountMoveDelete.Field()
