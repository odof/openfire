# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .account_tax_type import AccountTax, AccountTaxFilterInput


class AccountTaxQuery(graphene.ObjectType):
    _name = 'AccountTaxQuery'
    _type = 'query'

    account_taxs = graphene.List(
        graphene.NonNull(AccountTax),
        select=graphene.Argument(AccountTaxFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_account_taxs(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['account.tax']._prepare_graphql_domain(select=select, domain=domain)

        return env['account.tax'].search(odoo_domain, offset=offset, limit=limit)
