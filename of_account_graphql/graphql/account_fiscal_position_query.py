# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .account_fiscal_position_type import AccountFiscalPosition, AccountFiscalPositionFilterInput


class AccountFiscalPositionQuery(graphene.ObjectType):
    _name = 'AccountFiscalPositionQuery'
    _type = 'query'

    fiscal_positions = graphene.List(
        graphene.NonNull(AccountFiscalPosition),
        filter=graphene.Argument(AccountFiscalPositionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_fiscal_positions(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context["env"]
        odoo_domain = []
        odoo_type = {
            'id': 'int',
        }
        if domain:
            odoo_domain = graphqlOdooDomain(odoo_type, domain)

        if filter:
            if filter.tax_type_use:
                odoo_domain += [('tax_ids.tax_src_id.type_tax_use', '=', filter.tax_type_use.value)]
            if filter.name:
                odoo_domain += [('name', 'like', filter.name)]

        return env['account.fiscal.position'].search(odoo_domain, offset=offset, limit=limit)
