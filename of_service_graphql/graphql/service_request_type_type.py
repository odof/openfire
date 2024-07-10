# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .service_request_stage_type import ServiceRequestStage, ServiceRequestStageInput


class ServiceRequestType(OdooObjectType):
    _name = 'ServiceRequestType'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.NonNull(graphene.String)
    stage_ids = graphene.List(graphene.NonNull(ServiceRequestStage), name='stages')


class ServiceRequestTypeInput(graphene.InputObjectType):
    _name = 'ServiceRequestTypeInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()
    stages = graphene.List(ServiceRequestStageInput)


class ServiceRequestTypeFilterInput(ServiceRequestTypeInput):
    _name = 'ServiceRequestTypeFilterInput'
