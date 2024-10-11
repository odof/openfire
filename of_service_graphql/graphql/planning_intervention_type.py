# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .service_request_type import ServiceRequest, ServiceRequestInput
from .service_request_type_type import ServiceRequestType, ServiceRequestTypeInput


class PlanningIntervention(OdooObjectType):
    _name = "PlanningIntervention"
    _type = "types"

    ttype = graphene.Field(ServiceRequestType)
    request = graphene.Field(ServiceRequest)

    @staticmethod
    def resolve_ttype(root, info):
        return root.of_type_id or None

    @staticmethod
    def resolve_request(root, info):
        return root.of_request_id or None


class PlanningInterventionInput(graphene.InputObjectType):
    _name = "PlanningInterventionInput"
    _type = "types"

    ttype = graphene.Field(ServiceRequestTypeInput)
    request = graphene.Field(ServiceRequestInput)
