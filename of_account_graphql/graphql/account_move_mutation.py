import graphene

from odoo.addons.of_account_graphql.graphql.account_fiscal_position_mutation import (
    AccountFiscalPositionCreate,
    AccountFiscalPositionUpdate,
)
from odoo.addons.of_base_graphql.graphql.partner_mutation import PartnerCreate, PartnerUpdate
from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .account_fiscal_position_type import AccountFiscalPositionInput
from .account_move_line_mutation import AccountMoveLineCreate, AccountMoveLineUpdate
from .account_move_line_type import AccountMoveLineInput
from .account_move_type import AccountMove, AccountMoveCreateInput, AccountMoveUpdateInput


class AccountMoveCreate(graphene.Mutation):
    _name = 'AccountMoveCreate'

    class Arguments:
        input = AccountMoveCreateInput(required=True)
        partner = PartnerInput()
        lines = AccountMoveLineInput()
        fiscal_position = AccountFiscalPositionInput()

    Output = AccountMove

    def mutate(self, info, input, partner=None, lines=None, fiscal_position=None):
        env = info.context["env"]
        create_lines = env['account.move.line']

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if lines:
            for line in lines:
                if line.id:
                    line = AccountMoveLineUpdate().mutate(info, id=line.id, input=line)
                else:
                    line = AccountMoveLineCreate().miutate(info, input=line)
                create_lines += line

        if fiscal_position:
            if fiscal_position.id:
                fiscal_position = AccountFiscalPositionUpdate().mutate(
                    info, id=fiscal_position.id, input=fiscal_position
                )
            else:
                fiscal_position = AccountFiscalPositionCreate().mutate(info, input=fiscal_position)

        account_move = lazy_create(env, "account.move", input)

        if partner:
            account_move.partner_id = partner

        if lines:
            account_move.invoice_line_ids = [(6, 0, create_lines.ids)]

        if fiscal_position:
            account_move.fiscal_position_id = fiscal_position

        return account_move


class AccountMoveUpdate(graphene.Mutation):
    _name = 'AccountMoveUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = AccountMoveUpdateInput(required=True)
        partner = PartnerInput()
        lines = AccountMoveLineInput()
        fiscal_position = AccountFiscalPositionInput()

    Output = AccountMove

    def mutate(self, info, id, input, partner=None, lines=None, fiscal_position=None):
        env = info.context["env"]
        update_lines = env['account.move.line']

        if partner:
            if partner.id:
                partner = PartnerUpdate().mutate(info, id=partner.id, input=partner)
            else:
                partner = PartnerCreate().mutate(info, input=partner)

        if lines:
            for line in lines:
                if line.id:
                    line = AccountMoveLineUpdate().mutate(info, id=line.id, input=line)
                else:
                    line = AccountMoveLineCreate().miutate(info, input=line)
                update_lines += line

        if fiscal_position:
            if fiscal_position.id:
                fiscal_position = AccountFiscalPositionUpdate().mutate(
                    info, id=fiscal_position.id, input=fiscal_position
                )
            else:
                fiscal_position = AccountFiscalPositionCreate().mutate(info, input=fiscal_position)

        account_move = lazy_update(env, "account.move", id, input)

        if partner:
            account_move.partner_id = partner

        if lines:
            account_move.invoice_line_ids = [(6, 0, update_lines.ids)]

        if fiscal_position:
            account_move.fiscal_position_id = fiscal_position

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
