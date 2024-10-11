# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .stock_location_type import StockLocation, StockLocationFilterInput


class StockLocationQuery(graphene.ObjectType):
    _name = "StockLocationQuery"
    _type = "query"

    stock_locations = graphene.List(
        graphene.NonNull(StockLocation),
        select=graphene.Argument(StockLocationFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_stock_locations(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["stock.location"]._prepare_graphql_domain(select=select, domain=domain)

        return env["stock.location"].search(odoo_domain, offset=offset, limit=limit)
