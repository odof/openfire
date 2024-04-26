# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.of_graphql.graphql.odoo_graphql import OdooGraphql

from ..graphql.product_brand_mutation import ProductBrandMutation
from ..graphql.product_brand_query import ProductBrandQuery
from ..graphql.product_brand_type import ProductBrand, ProductBrandFilterInput
from ..graphql.product_type import Product


class OFGraphql(models.AbstractModel):
    _inherit = 'of.graphql'

    def _of_product_brand_graphql_register(self, dbname):
        # ici on charge le graphql de ce module
        OdooGraphql.add(
            dbname,
            [
                ProductBrand,
                Product,
                ProductBrandFilterInput,
                ProductBrandQuery,
                ProductBrandMutation,
            ],
        )
