# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import AccountFiscalPosition
from odoo.addons.of_account_graphql.graphql.account_payment_term_type import AccountPaymentTerm, AccountPaymentTermInput
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput
from odoo.addons.of_graphql.graphql.user_type import User, UserInput

from .sale_order_line_type import SaleOrderLine, SaleOrderLineInput


class SaleOrder(OdooObjectType):
    _name = 'SaleOrder'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()
    state = graphene.String(required=True)
    require_signature = graphene.Boolean()
    date_order = graphene.DateTime()
    validity_date = graphene.Date()
    partner = graphene.Field(Partner)
    order_line = graphene.List(graphene.NonNull(SaleOrderLine), name="lines")
    vendor = graphene.Field(User)
    fiscal_position = graphene.Field(AccountFiscalPosition)
    payment_term = graphene.Field(AccountPaymentTerm)

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None

    @staticmethod
    def resolve_vendor(root, info):
        return root.user_id or None

    @staticmethod
    def resolve_fiscal_position(root, info):
        return root.fiscal_position_id or None

    @staticmethod
    def resolve_payment_term(root, info):
        return root.payment_term_id or None


class SaleOrderInput(graphene.InputObjectType):
    _name = 'SaleOrderInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    date_order = graphene.DateTime()
    validity_date = graphene.Date()
    partner = graphene.Field(PartnerInput)
    lines = graphene.List(graphene.NonNull(SaleOrderLineInput))
    vendor = graphene.Field(UserInput)
    state = graphene.String()
    payment_term = graphene.Field(AccountPaymentTermInput)


class SaleOrderFilterInput(SaleOrderInput):
    _name = 'SaleOrderFilterInput'
