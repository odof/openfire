# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .stock_move_type import StockMove, StockMoveFilterInput


class StockMoveQuery(graphene.ObjectType):
    _name = "StockMoveQuery"
    _type = "query"

    stock_moves = graphene.List(
        graphene.NonNull(StockMove),
        select=graphene.Argument(StockMoveFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_stock_moves(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["stock.move"]._prepare_graphql_domain(select=select, domain=domain)

        return env["stock.move"].search(odoo_domain, offset=offset, limit=limit)
