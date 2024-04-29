import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .account_payment_type import AccountPayment


class AccountPaymentCreate(graphene.Mutation):
    _name = 'AccountPaymentCreate'

    class Arguments:
        name = graphene.String()
        amount_total = graphene.Float()
        amount_residual = graphene.Float()
        payment_state = graphene.String()
        date = graphene.Date()

    Output = AccountPayment

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['account.payment']._prepare_mutation_values(**args)
        return env['account.payment'].create(values)


class AccountPaymentUpdate(graphene.Mutation):
    _name = 'AccountPaymentUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        amount_total = graphene.Float()
        amount_residual = graphene.Float()
        payment_state = graphene.String()
        date = graphene.Date()

    Output = AccountPayment

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env['account.payment']._prepare_mutation_values(**args)
        account_payment = env['account.payment'].search([('id', '=', id)])
        account_payment.write(values)
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
