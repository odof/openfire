# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_button_toggle_mobile(self):
        self.ensure_one()
        self.of_mobile_available = not self.of_mobile_available
