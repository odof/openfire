# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfProductBrandAddProducts(models.TransientModel):
    _name = 'of.product.brand.add.products'

    brand_id = fields.Many2one('of.product.brand', 'Brand', required=True)
    product_ids = fields.Many2many('product.product', string="Products")

    @api.multi
    def add_products(self):
        self.ensure_one()
        if self.product_ids:
            # Set products' new brand_id
            self.product_ids.write({'brand_id': self.brand_id.id})

            # Change products' default_code to fit brand required prefix
            product_prefix = self.brand_id.prefix + "_"
            for product in self.product_ids:
                if product.default_code.startswith(product_prefix):
                    continue
                ind = product.default_code.find("_")
                product.default_code = product_prefix + product.default_code[ind+1:]
        return True
