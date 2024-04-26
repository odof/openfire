import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .account_tax_type import AccountTax, AccountTaxType


class AccountTaxCreate(graphene.Mutation):
    _name = 'AccountTaxCreate'

    class Arguments:
        name = graphene.String(required=True)
        amount = graphene.Float(required=True)
        price_include = graphene.Boolean(required=True)
        type_tax_use = graphene.Argument(AccountTaxType, required=True)

    Output = AccountTax

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['account.tax']._prepare_mutation_values(**args)
        return env['account.tax'].create(values)


class AccountTaxUpdate(graphene.Mutation):
    _name = 'AccountTaxUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        amount = graphene.Float(required=True)
        price_include = graphene.Boolean(required=True)
        type_tax_use = graphene.Argument(AccountTaxType, required=True)

    Output = AccountTax

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['account.tax']._prepare_mutation_values(**args)
        account_tax = env['account.tax'].search([('id', '=', id)])
        return account_tax.write(values)


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
