# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.sale_order_template_line_query import SaleOrderTemplateLineQuery
from ..graphql.sale_order_template_line_type import (
    SaleOrderTemplateLine,
    SaleOrderTemplateLineFilterInput,
    SaleOrderTemplateLineInput,
)
from ..graphql.sale_order_template_query import SaleOrderTemplateQuery
from ..graphql.sale_order_template_type import SaleOrderTemplate, SaleOrderTemplateFilterInput, SaleOrderTemplateInput
from ..graphql.sale_order_type import SaleOrder, SaleOrderInput


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_sale_management_template_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                SaleOrderTemplate,
                SaleOrderTemplateInput,
                SaleOrderTemplateLine,
                SaleOrderTemplateQuery,
                SaleOrderTemplateLineQuery,
                SaleOrderTemplateLineFilterInput,
                SaleOrderTemplateLineInput,
                SaleOrderTemplateFilterInput,
                SaleOrder,
                SaleOrderInput,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            "SaleOrderMutation": {
                "sale_order_update": {
                    "sale_template": SaleOrderTemplateInput,
                },
                "sale_order_create": {
                    "sale_template": SaleOrderTemplateInput,
                },
            },
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
