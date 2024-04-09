import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .account_payment_type import AccountPayment, AccountPaymentCreateInput, AccountPaymentUpdateInput


class AccountPaymentCreate(graphene.Mutation):
    _name = 'AccountPaymentCreate'

    class Arguments:
        input = AccountPaymentCreateInput(required=True)

    Output = AccountPayment

    def mutate(self, info, input):
        env = info.context["env"]

        account_payment = lazy_create(env, 'account.payment', input)

        return account_payment


class AccountPaymentUpdate(graphene.Mutation):
    _name = 'AccountPaymentUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = AccountPaymentUpdateInput(required=True)

    Output = AccountPayment

    def mutate(self, info, id, input):
        env = info.context["env"]

        account_payment = lazy_update(env, 'account.payment', id, input)

        return account_payment


class AccountPaymentDelete(graphene.Mutation):
    _name = 'AccountPaymentDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = AccountPayment

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'account.payment', id)


class AccountPaymentMutation(graphene.ObjectType):
    _name = 'AccountPaymentMutation'
    _type = 'mutation'

    account_payment_create = AccountPaymentCreate.Field()
    account_payment_update = AccountPaymentUpdate.Field()
    account_payment_delete = AccountPaymentDelete.Field()
