# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class StockLot(OdooObjectType):
    _name = 'StockLot'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()


class StockLotInput(graphene.InputObjectType):
    _name = 'StockLotInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()


class StockLotFilterInput(StockLotInput):
    _name = 'StockLotFilterInput'


class StockLotCreateInput(StockLotInput):
    _name = 'StockLotCreateInput'


class StockLotUpdateInput(StockLotInput):
    _name = 'StockLotUpdateInput'
