# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .product_category_type import ProductCategory

logger = logging.getLogger(__name__)


class Product(OdooObjectType):
    _name = 'Product'
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    categ_id = graphene.Field(ProductCategory, name="category")
    list_price = graphene.Float(required=True)


class ProductInput(graphene.InputObjectType):
    _name = 'ProductInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    ref = graphene.String()
    list_price = graphene.Float()


class ProductFilterInput(ProductInput):
    _name = 'ProductFilterInput'


class ProductUpdateInput(ProductInput):
    _name = 'ProductUpdateInput'


class ProductCreateInput(ProductInput):
    _name = 'ProductCreateInput'
