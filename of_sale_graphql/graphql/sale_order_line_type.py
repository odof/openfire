# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_tax_type import AccountTax, AccountTaxInput
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput


class SaleOrderLine(OdooObjectType):
    _name = "SaleOrderLine"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    product = graphene.Field(Product, required=True)
    tax_id = graphene.List(graphene.NonNull(AccountTax), name="taxes")
    product_uom_qty = graphene.Float(required=True)
    price_unit = graphene.Float(required=True)
    price_subtotal = graphene.Float()

    @staticmethod
    def resolve_product(root, info):
        return root.product_id or None


class SaleOrderLineInput(graphene.InputObjectType):
    _name = "SaleOrderLineInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    product_uom_qty = graphene.Float()
    price_unit = graphene.Float()
    price_subtotal = graphene.Float()
    product = graphene.Field(ProductInput)
    taxes = graphene.List(graphene.NonNull(AccountTaxInput))


class SaleOrderLineFilterInput(SaleOrderLineInput):
    _name = "SaleOrderLineFilterInput"
