# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OfProductBrandAddProducts(models.TransientModel):
    _name = "of.product.brand.add.products"
    _description = "Add Products to Brand"

    brand_id = fields.Many2one(comodel_name="of.product.brand", string="Brand", required=True)
    product_ids = fields.Many2many(comodel_name="product.template", string="Products")

    def add_products(self):
        self.ensure_one()
        if self.product_ids:
            # Set products' new brand_id
            old_prefix_product_ids = {}
            for product in self.product_ids:
                old_prefix = product.brand_id and product.brand_id.use_prefix and product.brand_id.code or ""
                if old_prefix in old_prefix_product_ids:
                    old_prefix_product_ids[old_prefix] = product
                else:
                    old_prefix_product_ids[old_prefix] += product

            self.product_ids.write({"brand_id": self.brand_id.id})

            for old_prefix, products in old_prefix_product_ids.items():
                self.brand_id.update_products_default_code(products, remove_previous_prefix=old_prefix)
