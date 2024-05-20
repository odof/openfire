# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .service_request_type import ServiceRequest, ServiceRequestFilterInput


class ServiceRequestQuery(graphene.ObjectType):
    _name = 'ServiceRequestQuery'
    _type = 'query'

    service_requests = graphene.List(
        graphene.NonNull(ServiceRequest),
        select=graphene.Argument(ServiceRequestFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_service_requests(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env['of.service.request']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.service.request'].search(odoo_domain, offset=offset, limit=limit)
