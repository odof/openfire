# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType


class ServiceRequestStage(OdooObjectType):
    _name = 'ServiceRequestStage'
    _type = 'types'

    id = graphene.Int(required=True)
    name = graphene.String()


class ServiceRequestStageInput(graphene.InputObjectType):
    _name = 'ServiceRequestStageInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()


class ServiceRequestStageFilterInput(ServiceRequestStageInput):
    _name = 'ServiceRequestStageFilterInput'
