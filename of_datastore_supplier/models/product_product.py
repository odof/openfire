# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    of_template_image = fields.Binary(related="product_tmpl_id.image_1920", string="Template Image")

    def read(self, fields=None, load="_classic_read"):
        if "standard_price" in fields and "of_product_user_id" not in self.env:
            self = self.with_context(of_product_user_id=self.env.user.id)
        return super().read(fields=fields, load=load)
