# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.account_fiscal_position_mutation import AccountFiscalPositionMutation
from ..graphql.account_fiscal_position_query import AccountFiscalPositionQuery
from ..graphql.account_fiscal_position_tax_type import (
    AccountFiscalPositionTax,
    AccountFiscalPositionTaxCreateInput,
    AccountFiscalPositionTaxUpdateInput,
)
from ..graphql.account_fiscal_position_type import (
    AccountFiscalPosition,
    AccountFiscalPositionCreateInput,
    AccountFiscalPositionUpdateInput,
)
from ..graphql.account_move_line_mutation import AccountMoveLineMutation
from ..graphql.account_move_line_query import AccountMoveLineQuery
from ..graphql.account_move_line_type import (
    AccountMoveLine,
    AccountMoveLineCreateInput,
    AccountMoveLineFilterInput,
    AccountMoveLineUpdateInput,
)
from ..graphql.account_move_mutation import AccountMoveMutation
from ..graphql.account_move_query import AccountMoveQuery
from ..graphql.account_move_type import (
    AccountMove,
    AccountMoveCreateInput,
    AccountMoveFilterInput,
    AccountMoveUpdateInput,
)
from ..graphql.account_tax_mutation import AccountTaxMutation
from ..graphql.account_tax_query import AccountTaxQuery
from ..graphql.account_tax_type import AccountTax, AccountTaxCreateInput, AccountTaxFilterInput, AccountTaxUpdateInput
from ..graphql.company_type import Company
from ..graphql.product_type import Product


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
                AccountFiscalPositionTaxCreateInput,
                AccountFiscalPositionTaxUpdateInput,
                AccountFiscalPosition,
                AccountFiscalPositionCreateInput,
                AccountFiscalPositionUpdateInput,
                AccountMove,
                AccountMoveUpdateInput,
                AccountMoveCreateInput,
                AccountMoveLineCreateInput,
                AccountMoveLineFilterInput,
                AccountMoveFilterInput,
                AccountMoveLine,
                AccountMoveLineUpdateInput,
                AccountTax,
                Product,
                AccountMoveQuery,
                AccountMoveMutation,
                AccountMoveLineQuery,
                AccountMoveLineMutation,
                AccountTaxMutation,
                AccountTaxQuery,
                AccountTaxFilterInput,
                AccountTaxCreateInput,
                AccountTaxUpdateInput,
            ],
        )
