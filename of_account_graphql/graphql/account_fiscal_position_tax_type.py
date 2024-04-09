# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType

from .account_tax_type import AccountTax


class AccountFiscalPositionTax(OdooObjectType):
    _name = 'AccountFiscalPositionTax'
    _type = 'types'

    id = graphene.Int(required=True)
    tax_src = graphene.Field(AccountTax, required=True)
    tax_dest = graphene.Field(AccountTax)

    @staticmethod
    def resolve_tax_src(root, info):
        return root.tax_src_id

    @staticmethod
    def resolve_tax_dest(root, info):
        return root.tax_dest_id or None


class AccountFiscalPositionTaxInput(graphene.InputObjectType):
    _name = "AccountFiscalPositionTaxInput"
    _type = "types"

    id = graphene.Int()
    name = graphene.String()


class AccountFiscalPositionTaxFilterInput(AccountFiscalPositionTaxInput):
    _name = "AccountFiscalPositionTaxFilterInput"


class AccountFiscalPositionTaxCreateInput(AccountFiscalPositionTaxInput):
    _name = "AccountFiscalPositionTaxCreateInput"


class AccountFiscalPositionTaxUpdateInput(AccountFiscalPositionTaxInput):
    _name = "AccountFiscalPositionTaxUpdateInput"
