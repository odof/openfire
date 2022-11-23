# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
from odoo import models, api

LIMIT_CHAR = 120


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def name_get(self):
        products_names = super(ProductProduct, self).name_get()
        if not self._context.get('show_shorten_name', False):
            return products_names
        limit_char = self._context.get('show_shorten_name', LIMIT_CHAR)
        if limit_char > 0:
            return [(product_name[0], '%s...' % product_name[1][:int(limit_char)]) for product_name in products_names]
        return products_names
