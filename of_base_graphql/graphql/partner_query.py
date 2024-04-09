import logging

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .partner_type import Partner, PartnerFilterInput

logger = logging.getLogger(__name__)


class PartnerQuery(graphene.ObjectType):
    _name = 'PartnerQuery'
    _type = 'query'

    partners = graphene.List(
        graphene.NonNull(Partner),
        filter=graphene.Argument(PartnerFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_partners(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
            'company_id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]
            if filter.street:
                odoo_domain += [('street', 'ilike', filter.street)]
            if filter.street2:
                odoo_domain += [('street2', 'ilike', filter.street2)]
            if filter.city:
                odoo_domain += [('city', 'ilike', filter.city)]
            if filter.zip:
                odoo_domain += [('zip', 'ilike', filter.zip)]
            if filter.email:
                odoo_domain += [('email', 'ilike', filter.email)]

        return env['res.partner'].search(odoo_domain, offset=offset, limit=limit)
