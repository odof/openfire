# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class ServiceRequestType(OdooObjectType):
    _name = 'ServiceRequestType'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()


class ServiceRequestTypeInput(graphene.InputObjectType):
    _name = 'ServiceRequestTypeInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()


class ServiceRequestTypeFilterInput(ServiceRequestTypeInput):
    _name = 'ServiceRequestTypeFilterInput'


class ServiceRequestTypeCreateInput(ServiceRequestTypeInput):
    _name = 'ServiceRequestTypeCreateInput'


class ServiceRequestTypeUpdateInput(ServiceRequestTypeInput):
    _name = 'ServiceRequestTypeUpdateInput'
