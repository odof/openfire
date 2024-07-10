# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .product_category_type import ProductCategory, ProductCategoryInput


class Product(OdooObjectType):
    _name = 'Product'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    categ_id = graphene.Field(ProductCategory, name="category")
    list_price = graphene.Float(required=True)


class ProductInput(graphene.InputObjectType):
    _name = 'ProductInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    list_price = graphene.Float()
    categ_id = graphene.Field(ProductCategoryInput, name="category")


class ProductFilterInput(ProductInput):
    _name = 'ProductFilterInput'
