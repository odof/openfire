# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .service_request_type import ServiceRequest
from .service_request_type_type import ServiceRequestType


class PlanningIntervention(OdooObjectType):
    _name = 'PlanningIntervention'
    _type = 'types'

    type = graphene.Field(ServiceRequestType)
    request = graphene.Field(ServiceRequest)

    @staticmethod
    def resolve_type(root, info):
        return root.of_type_id or None

    @staticmethod
    def resolve_request(root, info):
        return root.of_request_id or None
