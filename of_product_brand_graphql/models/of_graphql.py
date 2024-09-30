# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.product_brand_mutation import ProductBrandMutation
from ..graphql.product_brand_query import ProductBrandQuery
from ..graphql.product_brand_type import ProductBrand, ProductBrandFilterInput, ProductBrandInput
from ..graphql.product_type import Product


class OFGraphql(models.AbstractModel):
    _inherit = "of.graphql"

    def _of_product_brand_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                ProductBrand,
                Product,
                ProductBrandInput,
                ProductBrandFilterInput,
                ProductBrandQuery,
                ProductBrandMutation,
            ],
        )

    def _prepare_arguments(self):
        arguments = super()._prepare_arguments()

        new_arguments = {
            "ProductMutation": {
                "product_create": {
                    "brand": ProductBrandInput,
                },
                "product_update": {
                    "brand": ProductBrandInput,
                },
            },
        }
        arguments = self._add_arguments(new_arguments, arguments)

        return arguments
