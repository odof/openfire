# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.product_type import Product, ProductInput


class AccountMoveLine(OdooObjectType):
    _name = 'AccountMoveLine'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    product = graphene.Field(Product)
    quantity = graphene.Int()
    price_unit = graphene.Float()

    @staticmethod
    def resolve_product(root, info):
        return root.product_id or None


class AccountMoveLineInput(graphene.InputObjectType):
    _name = 'AccountMoveLineUpdateInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    quantity = graphene.Int()
    price_unit = graphene.Float()
    product = graphene.Field(ProductInput)


class AccountMoveLineFilterInput(AccountMoveLineInput):
    _name = 'AccountMoveLineFilterInput'
