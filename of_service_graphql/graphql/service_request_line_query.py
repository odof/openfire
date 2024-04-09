# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .service_request_line_type import ServiceRequestLine, ServiceRequestLineFilterInput


class ServiceRequestLineQuery(graphene.ObjectType):
    _name = 'ServiceRequestLineQuery'
    _type = 'query'

    service_request_lines = graphene.List(
        graphene.NonNull(ServiceRequestLine),
        select=graphene.Argument(ServiceRequestLineFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_service_request_lines(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['of.service.request.line']._prepare_graphql_domain(select=select, domain=domain)

        return env['of.service.request.line'].search(odoo_domain, offset=offset, limit=limit)
