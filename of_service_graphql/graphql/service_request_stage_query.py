# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .service_request_stage_type import ServiceRequestStage, ServiceRequestStageFilterInput


class ServiceRequestStageQuery(graphene.ObjectType):
    _name = 'ServiceRequestStageQuery'
    _type = 'query'

    service_request_stages = graphene.List(
        graphene.NonNull(ServiceRequestStage),
        select=graphene.Argument(ServiceRequestStageFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_service_request_stages(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env['of.service.request.stage']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.service.request.stage'].search(odoo_domain, offset=offset, limit=limit)
