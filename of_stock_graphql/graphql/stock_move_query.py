# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .stock_move_type import StockMove, StockMoveFilterInput


class StockMoveQuery(graphene.ObjectType):
    _name = 'StockMoveQuery'
    _type = 'query'

    stock_moves = graphene.List(
        graphene.NonNull(StockMove),
        filter=graphene.Argument(StockMoveFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_stock_moves(root, info, filter=None, domain=None, offset=0, limit=10):
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

        return env['stock.move'].search(odoo_domain, offset=offset, limit=limit)
