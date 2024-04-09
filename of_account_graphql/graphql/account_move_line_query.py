import graphene

from odoo.addons.of_graphql.graphql.odoo_domain import OdooDomainInput
from odoo.addons.of_graphql.graphql.odoo_type import graphqlOdooDomain

from .account_move_line_type import AccountMoveLine, AccountMoveLineFilterInput


class AccountMoveLineQuery(graphene.ObjectType):
    _name = 'AccountMoveLineQuery'
    _type = "query"

    account_move_lines = graphene.List(
        graphene.NonNull(AccountMoveLine),
        filter=graphene.Argument(AccountMoveLineFilterInput),
        domain=graphene.List(graphene.NonNull(OdooDomainInput)),
        limit=graphene.Int(),
        offset=graphene.Int(),
    )

    @staticmethod
    def resolve_account_move_lines(root, info, filter=None, domain=None, offset=0, limit=10):
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

        return env['account.move.line'].search(odoo_domain, offset=offset, limit=limit)
