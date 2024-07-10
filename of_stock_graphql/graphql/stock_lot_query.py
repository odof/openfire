# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .stock_lot_type import StockLot, StockLotFilterInput


class StockLotQuery(graphene.ObjectType):
    _name = 'StockLotQuery'
    _type = 'query'

    stock_lots = graphene.List(
        graphene.NonNull(StockLot),
        select=graphene.Argument(StockLotFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_stock_lots(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['stock.lot']._prepare_graphql_domain(select=select, domain=domain)

        return env['stock.lot'].search(odoo_domain, offset=offset, limit=limit)
