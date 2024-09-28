# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class RecoveryCylinder(OdooObjectType):
    _name = "RecoveryCylinder"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)


class RecoveryCylinderInput(graphene.InputObjectType):
    _name = "RecoveryCylinderInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class RecoveryCylinderFilterInput(RecoveryCylinderInput):
    _name = "RecoveryCylinderFilterInput"
