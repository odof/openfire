# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.account_payment_mutation import AccountPaymentMutation
from ..graphql.account_payment_query import AccountPaymentQuery
from ..graphql.account_payment_type import (
    AccountPayment,
    AccountPaymentCreateInput,
    AccountPaymentFilterInput,
    AccountPaymentUpdateInput,
)


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_account_payment_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                AccountPaymentQuery,
                AccountPayment,
                AccountPaymentFilterInput,
                AccountPaymentUpdateInput,
                AccountPaymentCreateInput,
                AccountPaymentMutation,
            ],
        )
