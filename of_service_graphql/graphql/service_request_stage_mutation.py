# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_graphql import lazy_delete

from .service_request_stage_type import ServiceRequestStage


class ServiceRequestStageCreate(graphene.Mutation):
    _name = "ServiceRequestStageCreate"

    class Arguments:
        name = graphene.String()

    Output = ServiceRequestStage

    def mutate(self, info, **args):
        env = info.context["env"]
        values = env["of.service.request.stage"]._prepare_mutation_values(**args)
        return env["of.service.request.stage"].create(values)


class ServiceRequestStageUpdate(graphene.Mutation):
    _name = "ServiceRequestStageUpdate"

    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()

    Output = ServiceRequestStage

    def mutate(self, info, id, **args):
        env = info.context["env"]
        values = env["of.service.request.stage"]._prepare_mutation_values(**args)
        request_stage = env["of.service.request.stage"].search([("id", "=", id)])
        request_stage.write(values)
        return request_stage


class ServiceRequestStageDelete(graphene.Mutation):
    _name = "ServiceRequestStageDelete"

    class Arguments:
        id = graphene.Int(required=True)

    Output = ServiceRequestStage

    def mutate(self, info, id):
        env = info.context["env"]
        return lazy_delete(env, "of.service.request.stage", id)


class ServiceRequestStageMutation(graphene.ObjectType):
    _name = "ServiceRequestStageMutation"
    _type = "mutation"

    service_request_stage_create = ServiceRequestStageCreate.Field()
    service_request_stage_update = ServiceRequestStageUpdate.Field()
    service_request_stage_delete = ServiceRequestStageDelete.Field()
