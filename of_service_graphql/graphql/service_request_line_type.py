# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_move_line_type import AccountMoveLine, AccountMoveLineInput
from odoo.addons.of_base_graphql.graphql.company_type import CompanyInput
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput
from odoo.addons.of_graphql.graphql.company_type import Company
from odoo.addons.of_sale_graphql.graphql.sale_order_line_type import SaleOrderLine, SaleOrderLineInput


class ServiceRequestLine(OdooObjectType):
    _name = "ServiceRequestLine"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    product = graphene.Field(Product)
    order_line = graphene.Field(SaleOrderLine)
    company = graphene.Field(Company)
    qty = graphene.Float()
    price_unit = graphene.Float()
    price_subtotal = graphene.Float()
    price_tax = graphene.Float()
    price_total = graphene.Float()
    invoice_status = graphene.String()
    qty_invoiced = graphene.Float()
    qty_invoiceable = graphene.Float()
    invoice_line_ids = graphene.List(graphene.NonNull(AccountMoveLine), name="invoiceLines")

    @staticmethod
    def resolve_product(root, info):
        return root.product_id or None

    @staticmethod
    def resolve_order_line(root, info):
        return root.order_line_id or None

    @staticmethod
    def resolve_company(root, info):
        return root.company_id or None


class ServiceRequestLineInput(graphene.InputObjectType):
    _name = "ServiceRequestLineInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    qty = graphene.Float()
    price_unit = graphene.Float()
    price_subtotal = graphene.Float()
    price_tax = graphene.Float()
    price_total = graphene.Float()
    invoice_status = graphene.String()
    qty_invoiced = graphene.Float()
    qty_invoiceable = graphene.Float()
    product = graphene.Field(ProductInput)
    order_line = graphene.Field(SaleOrderLineInput)
    company = graphene.Field(CompanyInput)
    invoice_lines = graphene.List(graphene.NonNull(AccountMoveLineInput))


class ServiceRequestLineFilterInput(ServiceRequestLineInput):
    _name = "ServiceRequestLineFilterInput"
