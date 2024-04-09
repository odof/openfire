import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_tax_type import AccountTax
from odoo.addons.of_base_graphql.graphql.product_type import Product


class SaleOrderLine(OdooObjectType):
    _name = 'SaleOrderLine'
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    product = graphene.Field(Product)
    tax_id = graphene.List(graphene.NonNull(AccountTax), name='taxes')
    product_uom_qty = graphene.Float()
    price_unit = graphene.Float()
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


class SaleOrderLineFilterInput(SaleOrderLineInput):
    _name = "SaleOrderLineFilterInput"


class SaleOrderLineCreateInput(SaleOrderLineInput):
    _name = "SaleOrderLineCreateInput"


class SaleOrderLineUpdateInput(SaleOrderLineInput):
    _name = "SaleOrderLineUpdateInput"
