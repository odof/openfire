# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.partner_type import Partner
from ..graphql.utm_source_type import UtmSource


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_crm_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                UtmSource,
                Partner,
            ],
        )
