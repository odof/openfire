# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .account_move_line_type import AccountMoveLine, AccountMoveLineFilterInput


class AccountMoveLineQuery(graphene.ObjectType):
    _name = 'AccountMoveLineQuery'
    _type = 'query'

    account_move_lines = graphene.List(
        graphene.NonNull(AccountMoveLine),
        select=graphene.Argument(AccountMoveLineFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_account_move_lines(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']

        odoo_domain = env['account.move.line']._prepare_graphql_domain(select=select, domain=domain)

        return env['account.move.line'].search(odoo_domain, offset=offset, limit=limit)
