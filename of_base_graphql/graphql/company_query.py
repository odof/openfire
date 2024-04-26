import graphene

from odoo.addons.of_graphql.graphql.company_type import Company
from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .company_type import CompanyFilterInput


class CompanyQuery(graphene.ObjectType):
    _name = 'CompanyQuery'
    _type = 'query'

    companies = graphene.List(
        graphene.NonNull(Company),
        filter=graphene.Argument(CompanyFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_companies(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.id:
                odoo_domain += [('id', '=', filter.id)]
            if filter.name:
                odoo_domain += [('name', 'ilike', filter.name)]

        return env['res.company'].search(odoo_domain, offset=offset, limit=limit)
