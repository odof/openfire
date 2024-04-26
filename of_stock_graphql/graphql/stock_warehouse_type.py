# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_base_graphql.graphql.partner_type import Partner, PartnerInput


class StockWarehouse(OdooObjectType):
    _name = 'StockWarehouse'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()
    partner = graphene.Field(Partner)

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None


class StockWarehouseInput(graphene.InputObjectType):
    _name = 'StockWarehouseInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    partner = graphene.Field(PartnerInput)


class StockWarehouseFilterInput(StockWarehouseInput):
    _name = 'StockWarehouseFilterInput'
