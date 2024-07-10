# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
        env = info.context['env']
        odoo_domain = env['of.service.request']._prepare_graphql_domain(select=select, domain=domain)

        service_requests_final = env['of.service.request'].search(odoo_domain, offset=offset, limit=limit)
        # Trier les DI
        if select:
            if select.sort == 'nearest_end_date':
                service_requests_final = sorted(service_requests_final, key=lambda x: x[0].end_date)
            elif select.sort == 'nearest_distance':
                service_requests_final = sorted(
                    service_requests_final, key=lambda x: float('inf') if len(x) < 2 or x[1] is None else x[1]
                )
        return service_requests_final
