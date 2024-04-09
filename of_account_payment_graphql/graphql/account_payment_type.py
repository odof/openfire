# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class AccountPayment(OdooObjectType):
    _name = 'AccountPayment'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()
    amount_total = graphene.Float()
    amount_residual = graphene.Float()
    payment_state = graphene.String()
    date = graphene.Date()


class AccountPaymentInput(graphene.InputObjectType):
    _name = 'AccountPaymentInput'
    _type = 'types'

    name = graphene.String()
    amount_total = graphene.Float()
    amount_residual = graphene.Float()
    payment_state = graphene.String()
    date = graphene.Date()


class AccountPaymentFilterInput(AccountPaymentInput):
    _name = 'AccountPaymentFilterInput'


class AccountPaymentCreateInput(AccountPaymentInput):
    _name = 'AccountPaymentCreateInput'


class AccountPaymentUpdateInput(AccountPaymentInput):
    _name = 'AccountPaymentUpdateInput'
