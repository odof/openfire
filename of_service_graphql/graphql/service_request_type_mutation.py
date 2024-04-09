import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update
from odoo.addons.of_service_graphql.graphql.service_request_stage_mutation import (
    ServiceRequestStageCreate,
    ServiceRequestStageUpdate,
)

from .service_request_stage_type import ServiceRequestStageInput
from .service_request_type_type import ServiceRequestType, ServiceRequestTypeCreateInput, ServiceRequestTypeUpdateInput


class ServiceRequestTypeCreate(graphene.Mutation):
    _name = 'ServiceRequestTypeCreate'

    class Arguments:
        input = ServiceRequestTypeCreateInput(required=True)
        stages = graphene.List(graphene.NonNull(ServiceRequestStageInput))

    Output = ServiceRequestType

    def mutate(self, info, input, stages=None):
        env = info.context["env"]

        create_stages = env['of.service.request.stage']

        if stages:
            for stage in stages:
                if stage.id:
                    # on est sur une mise à jour
                    stage = ServiceRequestStageUpdate().mutate(info, id=stage.id, input=stage)
                else:
                    stage = ServiceRequestStageCreate().mutate(info, input=stage)
                create_stages += stage

        service_request_type = lazy_create(env, 'of.service.request.type', input)

        if create_stages:
            service_request_type.stage_ids = [(6, 0, create_stages.ids)]

        return service_request_type


class ServiceRequestTypeUpdate(graphene.Mutation):
    _name = 'ServiceRequestTypeUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ServiceRequestTypeUpdateInput(required=True)
        stages = graphene.List(graphene.NonNull(ServiceRequestStageInput))

    Output = ServiceRequestType

    def mutate(self, info, id, input, stages=None):
        env = info.context["env"]

        create_stages = env['of.service.request.stage']

        if stages:
            for stage in stages:
                if stage.id:
                    # on est sur une mise à jour
                    stage = ServiceRequestStageUpdate().mutate(info, id=stage.id, input=stage)
                else:
                    stage = ServiceRequestStageCreate().mutate(info, input=stage)
                create_stages += stage

        service_request_type = lazy_update(env, 'of.service.request.type', id, input)

        if create_stages:
            service_request_type.stage_ids = [(6, 0, create_stages.ids)]

        return service_request_type


class ServiceRequestTypeDelete(graphene.Mutation):
    _name = 'ServiceRequestTypeDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequestType

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.service.request.type', id)


class ServiceRequestTypeMutation(graphene.ObjectType):
    _name = 'ServiceRequestTypeMutation'
    _type = 'mutation'

    service_request_type_create = ServiceRequestTypeCreate.Field()
    service_request_type_update = ServiceRequestTypeUpdate.Field()
    service_request_type_delete = ServiceRequestTypeDelete.Field()
