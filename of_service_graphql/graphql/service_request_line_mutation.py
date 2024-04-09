import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_create, lazy_delete, lazy_update

from .service_request_line_type import ServiceRequestLine, ServiceRequestLineCreateInput, ServiceRequestLineUpdateInput


class ServiceRequestLineCreate(graphene.Mutation):
    _name = 'ServiceRequestLineCreate'

    class Arguments:
        input = ServiceRequestLineCreateInput(required=True)

    Output = ServiceRequestLine

    def mutate(self, info, input):
        env = info.context["env"]

        service_request_line = lazy_create(env, 'of.service.request.line', input)

        return service_request_line


class ServiceRequestLineUpdate(graphene.Mutation):
    _name = 'ServiceRequestLineUpdate'

    class Arguments:
        id = graphene.Int(required=True)
        input = ServiceRequestLineUpdateInput(required=True)

    Output = ServiceRequestLine

    def mutate(self, info, id, input):
        env = info.context["env"]

        service_request_line = lazy_update(env, 'of.service.request.line', id, input)

        return service_request_line


class ServiceRequestLineDelete(graphene.Mutation):
    _name = 'ServiceRequestLineDelete'

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequestLine

    def mutate(self, info, id):
        env = info.context['env']
        return lazy_delete(env, 'of.service.request.line', id)


class ServiceRequestLineMutation(graphene.ObjectType):
    _name = 'ServiceRequestLineMutation'
    _type = 'mutation'

    service_request_line_create = ServiceRequestLineCreate.Field()
    service_request_line_update = ServiceRequestLineUpdate.Field()
    service_request_line_delete = ServiceRequestLineDelete.Field()
