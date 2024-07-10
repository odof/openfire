# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput

from .of_payment_mode_type import PaymentMode, PaymentModeInput


class AccountPayment(OdooObjectType):
    _name = 'AccountPayment'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()
    amount = graphene.Float()
    payment_state = graphene.String()
    date = graphene.Date()
    payment_mode = graphene.Field(PaymentMode)
    partner = graphene.Field(Partner)

    @staticmethod
    def resolve_payment_mode(root, info):
        return root.of_payment_mode_id or None

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None


class AccountPaymentInput(graphene.InputObjectType):
    _name = 'AccountPaymentInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    amount = graphene.Float()
    payment_state = graphene.String()
    date = graphene.Date()
    payment_mode = graphene.Field(PaymentModeInput)
    partner = graphene.Field(PartnerInput)


class AccountPaymentFilterInput(AccountPaymentInput):
    _name = 'AccountPaymentFilterInput'
