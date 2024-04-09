import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner

from .sale_order_line_type import SaleOrderLine


class SaleOrder(OdooObjectType):
    _name = "SaleOrder"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    date_order = graphene.DateTime()
    validity_date = graphene.Date()
    partner = graphene.Field(Partner)
    order_line = graphene.List(graphene.NonNull(SaleOrderLine), name="lines")

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None


class SaleOrderInput(graphene.InputObjectType):
    _name = "SaleOrderInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    date_order = graphene.DateTime()
    validity_date = graphene.Date()


class SaleOrderUpdateInput(SaleOrderInput):
    _name = "SaleOrderUpdateInput"


class SaleOrderCreateInput(SaleOrderInput):
    _name = "SaleOrderCreateInput"


class SaleOrderFilterInput(SaleOrderInput):
    _name = "SaleOrderFilterInput"
