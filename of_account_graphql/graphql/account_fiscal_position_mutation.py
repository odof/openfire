import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .account_fiscal_position_type import (
    AccountFiscalPosition,
    AccountFiscalPositionCreateInput,
    AccountFiscalPositionUpdateInput,
)


class AccountFiscalPositionCreate(graphene.Mutation):
    _name = 'AccountFiscalPositionCreate'

    class Arguments:
        input = AccountFiscalPositionCreateInput(required=True)

    Output = AccountFiscalPosition

    def mutate(self, info, input):
        env = info.context["env"]

        account_fiscal_position = lazy_create(env, "account.fiscal.position", input)

        return account_fiscal_position


class AccountFiscalPositionUpdate(graphene.Mutation):
    _name = 'AccountFiscalPositionUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = AccountFiscalPositionUpdateInput(required=True)

    Output = AccountFiscalPosition

    def mutate(self, info, id, input):
        env = info.context["env"]

        account_fiscal_position = lazy_update(env, "account.fiscal.position", id, input)

        return account_fiscal_position


class AccountFiscalPositionDelete(graphene.Mutation):
    _name = 'AccountFiscalPositionDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = AccountFiscalPosition

    def mutate(self, info, id):
        env = info.context["env"]

        return lazy_delete(env, "account.fiscal.position", id)


class AccountFiscalPositionMutation(graphene.ObjectType):
    _name = 'AccountFiscalPositionMutation'
    _type = 'mutation'

    account_fiscal_position_create = AccountFiscalPositionCreate.Field()
    account_fiscal_position_update = AccountFiscalPositionUpdate.Field()
    account_fiscal_position_delete = AccountFiscalPositionDelete.Field()
