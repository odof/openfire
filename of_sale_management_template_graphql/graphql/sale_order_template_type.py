# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import (
    AccountFiscalPosition,
    AccountFiscalPositionInput,
)
from odoo.addons.of_account_graphql.graphql.account_payment_term_type import AccountPaymentTerm, AccountPaymentTermInput
from odoo.addons.of_graphql.graphql.company_type import Company

from .sale_order_template_line_type import SaleOrderTemplateLine, SaleOrderTemplateLineInput


class SaleOrderTemplate(OdooObjectType):
    _name = "SaleOrderTemplate"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    fiscal_position = graphene.Field(AccountFiscalPosition)
    payment_term = graphene.Field(AccountPaymentTerm)
    sale_order_template_line_ids = graphene.List(graphene.NonNull(SaleOrderTemplateLine), name="lines")
    company = graphene.Field(Company)

    @staticmethod
    def resolve_fiscal_position(root, info):
        return root.of_fiscal_position_id or None

    @staticmethod
    def resolve_payment_term(root, info):
        return root.of_payment_term_id or None

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None


class SaleOrderTemplateInput(graphene.InputObjectType):
    _name = "SaleOrderTemplateInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    fiscal_position = graphene.Field(AccountFiscalPositionInput)
    payment_term = graphene.Field(AccountPaymentTermInput)
    lines = graphene.List(graphene.NonNull(SaleOrderTemplateLineInput))


class SaleOrderTemplateFilterInput(SaleOrderTemplateInput):
    _name = "SaleOrderTemplateFilterInput"
