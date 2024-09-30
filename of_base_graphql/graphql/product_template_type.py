# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class ProductTemplate(OdooObjectType):
    _name = "ProductTemplate"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    list_price = graphene.Float()


class ProductTemplateInput(graphene.InputObjectType):
    _name = "ProductTemplateInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    list_price = graphene.Float()


class ProductTemplateFilterInput(ProductTemplateInput):
    _name = "ProductTemplateFilterInput"
