# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class SaleOrder(OdooObjectType):
    _name = "SaleOrder"
    _type = "types"

    of_notes = graphene.String(name="notes")


class SaleOrderInput(graphene.InputObjectType):
    _name = "SaleOrderInput"
    _type = "types"

    notes = graphene.String(name="notes")
