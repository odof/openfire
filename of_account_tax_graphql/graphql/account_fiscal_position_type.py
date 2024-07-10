# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.of_account_graphql.graphql.account_tax_type import AccountTax


class AccountFiscalPosition(OdooObjectType):
    _name = 'AccountFiscalPosition'
    _type = 'types'

    default_taxes = graphene.List(graphene.NonNull(AccountTax), required=True)

    def resolve_default_taxes(root, info):
        return root.of_default_tax_ids or []
