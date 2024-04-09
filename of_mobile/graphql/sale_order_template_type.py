# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class SaleOrderTemplate(OdooObjectType):
    _name = 'SaleOrderTemplate'
    _type = 'types'

    mobile = graphene.Boolean()


class SaleOrderTemplateInput(graphene.InputObjectType):
    _name = 'SaleOrderTemplateInput'
    _type = 'types'

    mobile = graphene.Boolean()


class SaleOrderTemplateFilterInput(SaleOrderTemplateInput):
    _name = 'SaleOrderTemplateFilterInput'
