# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput

from .account_move_type import AccountMove, AccountMoveFilterInput


class AccountMoveQuery(graphene.ObjectType):
    _name = 'AccountMoveQuery'
    _type = 'query'

    account_moves = graphene.List(
        graphene.NonNull(AccountMove),
        select=graphene.Argument(AccountMoveFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_account_moves(root, info, select=None, domain=None, offset=0, limit=10):
        env = info.context['env']
        odoo_domain = env['account.move']._prepare_graphql_domain(select=select, domain=domain)

        return env['account.move'].search(odoo_domain, offset=offset, limit=limit)
