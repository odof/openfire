# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .partner_type import Partner, PartnerFilterInput


class PartnerQuery(graphene.ObjectType):
    _name = "PartnerQuery"
    _type = "query"

    partners = graphene.List(
        graphene.NonNull(Partner),
        select=graphene.Argument(PartnerFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_partners(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = env["res.partner"]._prepare_graphql_domain(select=select, domain=domain)

        return env["res.partner"].search(odoo_domain, offset=offset, limit=limit)
