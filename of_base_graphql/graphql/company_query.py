# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.company_type import Company
from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .company_type import CompanyFilterInput


class CompanyQuery(graphene.ObjectType):
    _name = 'CompanyQuery'
    _type = 'query'

    companies = graphene.List(
        graphene.NonNull(Company),
        select=graphene.Argument(CompanyFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_companies(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['res.company']._prepare_graphql_domain(select=select, domain=domain)

        return env['res.company'].search(odoo_domain, offset=offset, limit=limit)
