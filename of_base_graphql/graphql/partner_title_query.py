import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .partner_title_type import PartnerTitle, PartnerTitleFilterInput


class PartnerTitleQuery(graphene.ObjectType):
    _name = 'PartnerTitleQuery'
    _type = 'query'

    partner_titles = graphene.List(
        graphene.NonNull(PartnerTitle),
        filter=graphene.Argument(PartnerTitleFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_partner_titles(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.used_for_phone:
                odoo_domain += [('of_used_for_phone', '=', filter.used_for_phone)]

        return env['res.partner.title'].search(odoo_domain, offset=offset, limit=limit)
