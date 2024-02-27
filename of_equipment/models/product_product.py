# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

LIMIT_CHAR = 120


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def name_get(self):
        products_names = super().name_get()
        if not self._context.get('show_shorten_name', False):
            return products_names

        limit_char = self._context.get('show_shorten_name', LIMIT_CHAR)
        if isinstance(limit_char, bool) or isinstance(limit_char, str) and not limit_char.isdigit():
            limit_char = LIMIT_CHAR
        if limit_char > 0:
            return [(product_name[0], f'{product_name[1][:int(limit_char)]}...') for product_name in products_names]
        return products_names
