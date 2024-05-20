# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .stock_warehouse_type import StockWarehouse, StockWarehouseFilterInput


class StockWarehouseQuery(graphene.ObjectType):
    _name = 'StockWarehouseQuery'
    _type = 'query'

    stock_warehouses = graphene.List(
        graphene.NonNull(StockWarehouse),
        select=graphene.Argument(StockWarehouseFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_stock_warehouses(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env['stock.warehouse']._prepare_graphql_domain(select=select, domain=domain)

        return env['stock.warehouse'].search(odoo_domain, offset=offset, limit=limit)
