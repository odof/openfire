# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def write(self, vals):
        # Update sale order template lines that have a product of updated brand
        # and that haven't been updated manually
        sale_order_tmpl_line_obj = self.env["sale.order.template.line"]
        tmpl_line_to_update = sale_order_tmpl_line_obj.browse()
        if any(field in vals for field in self.sale_order_template_management_fields()):
            for product in self:
                product_name = product._recompute_product_name()
                # get all sale order template lines with the same product name as the updated product
                tmpl_line_to_update |= sale_order_tmpl_line_obj.search(
                    [("product_id", "=", product.id), ("name", "=", product_name)]
                )

        res = super().write(vals)

        # update sale order template lines with new product name
        for tmpl_line in tmpl_line_to_update:
            product_name = tmpl_line.product_id._recompute_product_name()
            tmpl_line.update({"name": product_name})

        return res

    @api.model
    def sale_order_template_management_fields(self):
        return ["default_code", "name", "description_sale", "product_template_attribute_value_ids"]
