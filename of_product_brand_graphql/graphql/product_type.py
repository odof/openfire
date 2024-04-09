import graphene

from odoo.addons.graphql_base import OdooObjectType

from .product_brand_type import ProductBrand


class Product(OdooObjectType):
    _name = 'Product'
    _type = 'types'

    brand = graphene.Field(ProductBrand)

    @staticmethod
    def resolve_brand(root, info):
        return root.brand_id or None
