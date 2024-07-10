# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .service_request_type_type import ServiceRequestType, ServiceRequestTypeInput


class PlanningInterventionTemplate(OdooObjectType):
    _name = 'PlanningInterventionTemplate'
    _type = 'types'

    ttype = graphene.Field(ServiceRequestType)

    @staticmethod
    def resolve_ttype(root, info):
        return root.type_id or None


class PlanningInterventionTemplateInput(graphene.InputObjectType):
    _name = 'PlanningInterventionTemplateInput'
    _type = 'types'

    ttype = graphene.Field(ServiceRequestTypeInput)
