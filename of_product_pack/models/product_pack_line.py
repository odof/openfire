# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductPackLine(models.Model):
    _inherit = "product.pack.line"

    component_price = fields.Float(related="product_id.list_price")

    def write(self, vals):
        res = super().write(vals)
        self._update_product_template_list_price(vals)
        return res

    def _update_product_template_list_price(self, vals):
        if any(field in ["quantity", "product_id", "component_price"] for field in vals):
            for product in (
                self.mapped("parent_product_id")
                .mapped("product_tmpl_id")
                .filtered(lambda pt: pt.pack_ok and pt.pack_component_price == "totalized")
                .with_context(of_pack_avoid_recompute_list_price=True)
            ):
                product.list_price = sum(
                    pack_line.component_price * pack_line.quantity for pack_line in product.pack_line_ids
                )
