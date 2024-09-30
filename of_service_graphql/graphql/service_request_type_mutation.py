# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .service_request_stage_type import ServiceRequestStageInput
from .service_request_type_type import ServiceRequestType


class ServiceRequestTypeCreate(graphene.Mutation):
    _name = "ServiceRequestTypeCreate"

    class Arguments:
        name = graphene.String()
        stages = graphene.List(graphene.NonNull(ServiceRequestStageInput))

    Output = ServiceRequestType

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["of.service.request.type"]._prepare_mutation_values(**args)
        return env["of.service.request.type"].create(values)


class ServiceRequestTypeUpdate(graphene.Mutation):
    _name = "ServiceRequestTypeUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        stages = graphene.List(graphene.NonNull(ServiceRequestStageInput))

    Output = ServiceRequestType

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["of.service.request.type"]._prepare_mutation_values(**args)
        request_type = env["of.service.request.type"].search([("id", "=", id)])
        request_type.write(values)
        return request_type


class ServiceRequestTypeDelete(graphene.Mutation):
    _name = "ServiceRequestTypeDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequestType

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "of.service.request.type", id)


class ServiceRequestTypeMutation(graphene.ObjectType):
    _name = "ServiceRequestTypeMutation"
    _type = "mutation"

    service_request_type_create = ServiceRequestTypeCreate.Field()
    service_request_type_update = ServiceRequestTypeUpdate.Field()
    service_request_type_delete = ServiceRequestTypeDelete.Field()
