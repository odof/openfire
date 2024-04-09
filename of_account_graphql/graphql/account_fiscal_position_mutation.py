# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .account_fiscal_position_type import AccountFiscalPosition


class AccountFiscalPositionCreate(graphene.Mutation):
    _name = 'AccountFiscalPositionCreate'

    class Arguments:
        name = graphene.String(required=True)

    Output = AccountFiscalPosition

    def mutate(self, info, **args):
        env = info.context['env']
        value = env['account.fiscal.position']._prepare_mutation_values(**args)
        return env['account.fiscal.position'].create(value)


class AccountFiscalPositionUpdate(graphene.Mutation):
    _name = 'AccountFiscalPositionUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()

    Output = AccountFiscalPosition

    def mutate(self, info, id, **args):
        env = info.context['env']
        value = env['account.fiscal.position']._prepare_mutation_values(**args)
        fiscal_position = env['account.fiscal.position'].search([('id', '=', id)])
        fiscal_position.write(value)
        return fiscal_position


class AccountFiscalPositionDelete(graphene.Mutation):
    _name = 'AccountFiscalPositionDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = AccountFiscalPosition

    def mutate(self, info, id):
        env = info.context['env']

        return lazy_delete(env, 'account.fiscal.position', id)


class AccountFiscalPositionMutation(graphene.ObjectType):
    _name = 'AccountFiscalPositionMutation'
    _type = 'mutation'

    account_fiscal_position_create = AccountFiscalPositionCreate.Field()
    account_fiscal_position_update = AccountFiscalPositionUpdate.Field()
    account_fiscal_position_delete = AccountFiscalPositionDelete.Field()
