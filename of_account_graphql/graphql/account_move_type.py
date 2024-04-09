import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_fiscal_position_type import AccountFiscalPosition
from odoo.addons.of_base_graphql.graphql.partner_type import Partner

from .account_move_line_type import AccountMoveLine


class AccountMove(OdooObjectType):
    _name = 'AccountMove'
    _type = "types"

    id = graphene.Int()
    name = graphene.String()
    partner = graphene.Field(Partner)
    invoice_line_ids = graphene.List(AccountMoveLine, name='lines')
    fiscal_position = graphene.Field(AccountFiscalPosition)

    @staticmethod
    def resolve_partner(root, info):
        return root.partner_id or None

    @staticmethod
    def resolve_fiscal_position(root, info):
        return root.fiscal_position_id or None


class AccountMoveInput(graphene.InputObjectType):
    _name = 'AccountMoveInput'
    _type = 'types'

    id = graphene.Int()
    name = graphene.String()


class AccountMoveFilterInput(AccountMoveInput):
    _name = 'AccountMoveUpdateFilterInput'


class AccountMoveCreateInput(AccountMoveInput):
    _name = 'AccountMoveCreateInput'


class AccountMoveUpdateInput(AccountMoveInput):
    _name = 'AccountMoveUpdateInput'
