import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .service_request_type import ServiceRequest, ServiceRequestCreateInput, ServiceRequestUpdateInput


class ServiceRequestCreate(graphene.Mutation):
    _name = 'ServiceRequestCreate'

    class Arguments:
        input = ServiceRequestCreateInput(required=True)

    Output = ServiceRequest

    def mutate(self, info, input):
        env = info.context["env"]

        service_request = lazy_create(env, 'of.service.request', input)

        return service_request


class ServiceRequestUpdate(graphene.Mutation):
    _name = 'ServiceRequestUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ServiceRequestUpdateInput(required=True)

    Output = ServiceRequest

    def mutate(self, info, id, input):
        env = info.context["env"]

        service_request = lazy_update(env, 'of.service.request', id, input)

        return service_request


class ServiceRequestDelete(graphene.Mutation):
    _name = 'ServiceRequestDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequest

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.service.request', id)


class ServiceRequestMutation(graphene.ObjectType):
    _name = 'ServiceRequestMutation'
    _type = 'mutation'

    service_request_create = ServiceRequestCreate.Field()
    service_request_update = ServiceRequestUpdate.Field()
    service_request_delete = ServiceRequestDelete.Field()
