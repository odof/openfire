# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import graphene

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.sale_order_type import SaleOrder, SaleOrderInput


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_sale_crm_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                SaleOrder,
                SaleOrderInput,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            "SaleOrderMutation": {
                "sale_order_create": {
                    "notes": graphene.String(),
                },
                "sale_order_update": {
                    "notes": graphene.String(),
                },
            },
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
