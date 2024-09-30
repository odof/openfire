# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def unlink(self):
        deleted_ids = self.ids
        ir_config_param_obj = self.env["ir.config_parameter"].sudo()
        deposit_product_id = ir_config_param_obj.get_param("sale.default_deposit_product_id")
        res = super().unlink()
        if deposit_product_id in deleted_ids:
            deposit_product_id.set_param("sale.default_deposit_product_id", False)
        return res
