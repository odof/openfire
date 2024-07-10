# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class ProductCategory(OdooObjectType):
    _name = 'ProductCategory'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String(required=True)


class ProductCategoryInput(graphene.InputObjectType):
    _name = 'ProductCategoryInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()


class ProductCategoryFilterInput(ProductCategoryInput):
    _name = 'ProductCategoryFilterInput'
