import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner
from odoo.addons.of_base_graphql.graphql.product_type import Product


class StockMove(OdooObjectType):
    _name = "StockMove"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    partner = graphene.Field(Partner)
    product = graphene.Field(Product)

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None

    @staticmethod
    def resolve_product(root, info):
        return root.product_id or None


class StockMoveInput(graphene.InputObjectType):
    _name = "StockMoveInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class StockMoveUpdateInput(StockMoveInput):
    _name = "StockMoveUpdateInput"


class StockMoveCreateInput(StockMoveInput):
    _name = "StockMoveCreateInput"


class StockMoveFilterInput(StockMoveInput):
    _name = "StockMoveFilterInput"
