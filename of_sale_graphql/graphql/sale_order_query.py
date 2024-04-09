# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .sale_order_type import SaleOrder, SaleOrderFilterInput


class SaleOrderQuery(graphene.ObjectType):
    _name = 'SaleOrderQuery'
    _type = 'query'

    sales = graphene.List(
        graphene.NonNull(SaleOrder),
        filter=graphene.Argument(SaleOrderFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_sales(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = []
        odoo_type = {'id': 'int'}
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'like', filter.name)]

        return env['sale.order'].search(odoo_domain, offset=offset, limit=limit)
