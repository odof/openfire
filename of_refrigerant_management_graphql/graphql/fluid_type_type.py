# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class FluidCategory(graphene.Enum):
    CFC = "cfc"
    HCFC = "hcfc"
    HFC = "hfc"


class FluidType(OdooObjectType):
    _name = "FluidType"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    gwp = graphene.Float(required=True)
    category = graphene.Field(FluidCategory, required=True)


class FluidTypeInput(graphene.InputObjectType):
    _name = "FluidTypeInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class FluidTypeFilterInput(FluidTypeInput):
    _name = "FluidTypeFilterInput"
