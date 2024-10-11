# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .sale_order_template_type import SaleOrderTemplate, SaleOrderTemplateFilterInput


class SaleOrderTemplateQuery(graphene.ObjectType):
    _name = "SaleOrderTemplateQuery"
    _type = "query"

    sale_templates = graphene.List(
        graphene.NonNull(SaleOrderTemplate),
        select=graphene.Argument(SaleOrderTemplateFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_sale_templates(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["sale.order.template"]._prepare_graphql_domain(select=select, domain=domain)

        return env["sale.order.template"].search(odoo_domain, offset=offset, limit=limit)
