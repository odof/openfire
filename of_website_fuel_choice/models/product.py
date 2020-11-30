# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    @api.depends('image_variant', 'product_tmpl_id.image')
    def _compute_images(self):
        for product in self:
            if self._context.get('bin_size'):
                product.image_medium = product.image_variant
                product.image_small = product.image_variant
                product.image = product.image_variant
            else:
                resized_images = tools.image_get_resized_images(
                    product.image_variant, return_big=True, avoid_resize_medium=True)
                product.image_medium = resized_images['image_medium']
                product.image_small = resized_images['image_small']
                product.image = resized_images['image']
            if not product.image_medium:
                product.image_medium = product.product_tmpl_id.image_medium
            if not product.image_small:
                product.image_small = product.product_tmpl_id.image_small
            if not product.image:
                product.image = product.product_tmpl_id.image
