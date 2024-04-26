import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput

from .stock_location_type import StockLocation, StockLocationInput
from .stock_move_type import StockMove, StockMoveInput


class Picking(OdooObjectType):
    _name = "Picking"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    partner = graphene.Field(Partner)
    move_ids_without_package = graphene.List(StockMove, name='lines')
    location = graphene.Field(StockLocation)

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None

    @staticmethod
    def resolve_location(root, info):
        return root.location_id or None


class PickingInput(graphene.InputObjectType):
    _name = "PickingInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    partner = graphene.Field(PartnerInput)
    lines = graphene.List(StockMoveInput)
    location = graphene.Field(StockLocationInput)


class PickingFilterInput(PickingInput):
    _name = "PickingFilterInput"
