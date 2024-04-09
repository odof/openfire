import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .account_move_type import AccountMove, AccountMoveFilterInput


class AccountMoveQuery(graphene.ObjectType):
    _name = 'AccountMoveQuery'
    _type = "query"

    account_moves = graphene.List(
        graphene.NonNull(AccountMove),
        filter=graphene.Argument(AccountMoveFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_account_moves(root, info, filter=None, domain=None, offset=0, limit=10):
        env = info.context['env']
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

        return env['account.move'].search(odoo_domain, offset=offset, limit=limit)
