# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .sale_order_template_type import SaleOrderTemplate, SaleOrderTemplateInput


class SaleOrder(OdooObjectType):
    _name = "SaleOrder"
    _type = "types"

    sale_template = graphene.Field(SaleOrderTemplate)


class SaleOrderInput(graphene.InputObjectType):
    _name = "SaleOrderInput"
    _type = "types"

    sale_template = graphene.Field(SaleOrderTemplateInput)


class SaleOrderFilterInput(SaleOrderInput):
    _name = "SaleOrderFilterInput"
