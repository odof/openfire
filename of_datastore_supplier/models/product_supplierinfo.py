# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    def _convert_to_cache(self, values, update=False, validate=True):
        if "price" in values:
            values = self._handle_purchase_price_value_in_cache(values)
        return super()._convert_to_cache(values, update=update, validate=validate)

    def _handle_purchase_price_value_in_cache(self, values):
        """Distributors can't read the purchase price if they do not belong to the margin group"""
        group = self.env.ref("of_sale.of_group_sale_responsible", raise_if_not_found=False)
        user = self.env.user
        if user.of_is_distributor and group and not user.has_group("of_sale.of_group_sale_responsible"):
            values = dict(values)
            values["price"] = 0.0
        return values
