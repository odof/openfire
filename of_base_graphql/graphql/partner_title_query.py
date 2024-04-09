# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .partner_title_type import PartnerTitle, PartnerTitleFilterInput


class PartnerTitleQuery(graphene.ObjectType):
    _name = 'PartnerTitleQuery'
    _type = 'query'

    partner_titles = graphene.List(
        graphene.NonNull(PartnerTitle),
        select=graphene.Argument(PartnerTitleFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_partner_titles(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['res.partner.title']._prepare_graphql_domain(select=select, domain=domain)

        return env['res.partner.title'].search(odoo_domain, offset=offset, limit=limit)
