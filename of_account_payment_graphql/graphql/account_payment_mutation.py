import logging

import graphene

from odoo.addons.of_base_graphql.graphql.partner_type import PartnerInput
from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .account_payment_type import AccountPayment
from .of_payment_mode_type import PaymentModeInput

logger = logging.getLogger(__name__)


class AccountPaymentCreate(graphene.Mutation):
    _name = 'AccountPaymentCreate'

    class Arguments:
        name = graphene.String()
        amount = graphene.Float()
        payment_state = graphene.String()
        date = graphene.Date()
        payment_mode = graphene.Argument(PaymentModeInput)
        partner = graphene.Argument(PartnerInput)

    Output = AccountPayment

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env['account.payment']._prepare_mutation_values(**args)
        payment = env['account.payment'].create(values)
        payment.action_post()
        if invoice := payment.intervention_invoice_id:
            invoice.payment_id = payment.id
        return payment


class AccountPaymentUpdate(graphene.Mutation):
    _name = 'AccountPaymentUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        amount = graphene.Float()
        payment_state = graphene.String()
        date = graphene.Date()
        payment_mode = graphene.Argument(PaymentModeInput)
        partner = graphene.Argument(PartnerInput)

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
