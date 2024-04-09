import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .account_tax_type import AccountTax, AccountTaxCreateInput, AccountTaxUpdateInput


class AccountTaxCreate(graphene.Mutation):
    _name = 'AccountTaxCreate'

    class Arguments:
        input = AccountTaxCreateInput(required=True)

    Output = AccountTax

    def mutate(self, info, input):
        env = info.context["env"]

        account_tax = lazy_create(env, 'account.tax', input)

        return account_tax


class AccountTaxUpdate(graphene.Mutation):
    _name = 'AccountTaxUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = AccountTaxUpdateInput(required=True)

    Output = AccountTax

    def mutate(self, info, id, input):
        env = info.context["env"]

        account_tax = lazy_update(env, 'account.tax', id, input)

        return account_tax


class AccountTaxDelete(graphene.Mutation):
    _name = 'AccountTaxDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = AccountTax

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'account.tax', id)


class AccountTaxMutation(graphene.ObjectType):
    _name = 'AccountTaxMutation'
    _type = 'mutation'

    account_tax_create = AccountTaxCreate.Field()
    account_tax_update = AccountTaxUpdate.Field()
    account_tax_delete = AccountTaxDelete.Field()
