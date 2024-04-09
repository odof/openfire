# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .service_request_type_type import ServiceRequestType, ServiceRequestTypeFilterInput


class ServiceRequestTypeQuery(graphene.ObjectType):
    _name = 'ServiceRequestTypeQuery'
    _type = 'query'

    service_request_types = graphene.List(
        graphene.NonNull(ServiceRequestType),
        select=graphene.Argument(ServiceRequestTypeFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_service_request_types(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.service.request.type']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.service.request.type'].search(odoo_domain, offset=offset, limit=limit)
