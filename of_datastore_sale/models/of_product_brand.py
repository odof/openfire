# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models


class OFProductBrand(models.Model):
    _inherit = "of.product.brand"

    is_allow_dropshipping = fields.Boolean(string="Is Dropshipping ?")

    @api.model
    def dropshipping_allowed(self):
        return self.env.user.has_group("of_datastore_sale.of_group_datastore_brand_dropshipping")

    def write(self, vals):
        route = self.env.ref("stock_dropshipping.route_drop_shipping", raise_if_not_found=False)
        res = super().write(vals)
        if route and vals.get("is_allow_dropshipping"):
            self.mapped("product_ids").write({"route_ids": [Command.link(route.id)]})
        return res
