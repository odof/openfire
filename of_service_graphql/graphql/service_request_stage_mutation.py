import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .service_request_stage_type import (
    ServiceRequestStage,
    ServiceRequestStageCreateInput,
    ServiceRequestStageUpdateInput,
)


class ServiceRequestStageCreate(graphene.Mutation):
    _name = 'ServiceRequestStageCreate'

    class Arguments:
        input = ServiceRequestStageCreateInput(required=True)

    Output = ServiceRequestStage

    def mutate(self, info, input):
        env = info.context["env"]

        service_request_stage = lazy_create(env, 'of.service.request.stage', input)

        return service_request_stage


class ServiceRequestStageUpdate(graphene.Mutation):
    _name = 'ServiceRequestStageUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ServiceRequestStageUpdateInput(required=True)

    Output = ServiceRequestStage

    def mutate(self, info, id, input):
        env = info.context["env"]

        service_request_stage = lazy_update(env, 'of.service.request.stage', id, input)

        return service_request_stage


class ServiceRequestStageDelete(graphene.Mutation):
    _name = 'ServiceRequestStageDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequestStage

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.service.request.stage', id)


class ServiceRequestStageMutation(graphene.ObjectType):
    _name = 'ServiceRequestStageMutation'
    _type = 'mutation'

    service_request_stage_create = ServiceRequestStageCreate.Field()
    service_request_stage_update = ServiceRequestStageUpdate.Field()
    service_request_stage_delete = ServiceRequestStageDelete.Field()
