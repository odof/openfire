# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models


class OfProductBrand(models.Model):
    _inherit = "of.product.brand"

    def write(self, vals):
        # Update sale order template lines that have a product of updated brand
        # and that haven't been updated manually
        sale_order_tmpl_line_obj = self.env["sale.order.template.line"]
        tmpl_line_to_update = sale_order_tmpl_line_obj.browse()
        if any(field in vals for field in self.sale_order_template_management_fields()):
            for brand in self:
                # get all sale order template lines with product of updated brand
                tmpl_line_with_brand = sale_order_tmpl_line_obj.search([("product_id.brand_id", "=", brand.id)])
                for tmpl_line in tmpl_line_with_brand:
                    line_name = tmpl_line.product_id._recompute_product_name()
                    # store sale order template lines that haven't been updated and for which we need to update the name
                    if line_name == tmpl_line.name:
                        tmpl_line_to_update |= tmpl_line

        res = super().write(vals)

        # update sale order template lines with new product name
        for tmpl_line in tmpl_line_to_update:
            product_name = tmpl_line.product_id._recompute_product_name()
            tmpl_line.update({"name": product_name})
        return res

    @api.model
    def sale_order_template_management_fields(self):
        return ["use_brand_description_sale", "description_sale"]
