# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .account_fiscal_position_tax_type import AccountFiscalPositionTax
from .account_tax_type import AccountTaxType


class AccountFiscalPosition(OdooObjectType):
    _name = "AccountFiscalPosition"
    _type = "types"

    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    taxes = graphene.List(
        graphene.NonNull(AccountFiscalPositionTax),
        required=True,
    )

    @staticmethod
    def resolve_taxes(root, info):
        return root.tax_ids or []


class AccountFiscalPositionInput(graphene.InputObjectType):
    _name = "AccountFiscalPositionInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class AccountFiscalPositionFilterInput(AccountFiscalPositionInput):
    _name = "AccountFiscalPositionFilterInput"

    tax_type_use = graphene.Field(AccountTaxType)
