# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import (
    AccountFiscalPosition,
    AccountFiscalPositionFilterInput,
)
from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput


class AccountFiscalPositionQuery(graphene.ObjectType):
    _name = 'AccountFiscalPositionQuery'
    _type = 'query'

    fiscal_positions = graphene.List(
        graphene.NonNull(AccountFiscalPosition),
        select=graphene.Argument(AccountFiscalPositionFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_fiscal_positions(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context["env"]

        odoo_domain = env['account.fiscal.position']._prepare_graphql_domain(select=select, domain=domain)

        return env['account.fiscal.position'].search(odoo_domain, offset=offset, limit=limit)
