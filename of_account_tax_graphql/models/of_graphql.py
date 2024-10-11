# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.account_fiscal_position_type import AccountFiscalPosition


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_account_tax_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [AccountFiscalPosition],
        )
