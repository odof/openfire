# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.account_fiscal_position_mutation import AccountFiscalPositionMutation
from ..graphql.account_fiscal_position_query import AccountFiscalPositionQuery
from ..graphql.account_fiscal_position_tax_type import AccountFiscalPositionTax
from ..graphql.account_fiscal_position_type import AccountFiscalPosition
from ..graphql.account_move_line_mutation import AccountMoveLineMutation
from ..graphql.account_move_line_query import AccountMoveLineQuery
from ..graphql.account_move_line_type import AccountMoveLine, AccountMoveLineFilterInput
from ..graphql.account_move_mutation import AccountMoveMutation
from ..graphql.account_move_query import AccountMoveQuery
from ..graphql.account_move_type import AccountMove, AccountMoveFilterInput
from ..graphql.account_tax_mutation import AccountTaxMutation
from ..graphql.account_tax_query import AccountTaxQuery
from ..graphql.account_tax_type import AccountTax, AccountTaxFilterInput
from ..graphql.company_type import Company
from ..graphql.product_type import Product, ProductInput


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_account_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                Company,
                AccountFiscalPositionMutation,
                AccountFiscalPositionQuery,
                AccountFiscalPositionTax,
                AccountFiscalPosition,
                AccountMove,
                AccountMoveLineFilterInput,
                AccountMoveFilterInput,
                AccountMoveLine,
                AccountTax,
                Product,
                ProductInput,
                AccountMoveQuery,
                AccountMoveMutation,
                AccountMoveLineQuery,
                AccountMoveLineMutation,
                AccountTaxMutation,
                AccountTaxQuery,
                AccountTaxFilterInput,
            ],
        )
