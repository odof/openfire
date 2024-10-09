# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.onchange("brand_id")
    def _onchange_brand_id(self):
        super()._onchange_brand_id()
        if self.brand_id and self.brand_id.is_allow_dropshipping:
            if route := self.env.ref("stock_dropshipping.route_drop_shipping", raise_if_not_found=False):
                self.route_ids |= route
