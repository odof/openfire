# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .sale_order_line_type import SaleOrderLine, SaleOrderLineFilterInput


class SaleOrderLineQuery(graphene.ObjectType):
    _name = "SaleOrderLineQuery"
    _type = "query"

    sale_lines = graphene.List(
        graphene.NonNull(SaleOrderLine),
        select=graphene.Argument(SaleOrderLineFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_sale_lines(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["sale.order.line"]._prepare_graphql_domain(select=select, domain=domain)

        return env["sale.order.line"].search(odoo_domain, offset=offset, limit=limit)
