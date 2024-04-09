# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .sale_order_type import SaleOrder, SaleOrderFilterInput


class SaleOrderQuery(graphene.ObjectType):
    _name = 'SaleOrderQuery'
    _type = 'query'

    sales = graphene.List(
        graphene.NonNull(SaleOrder),
        select=graphene.Argument(SaleOrderFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_sales(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['sale.order']._prepare_graphql_domain(select=select, domain=domain)

        return env['sale.order'].search(odoo_domain, offset=offset, limit=limit)
