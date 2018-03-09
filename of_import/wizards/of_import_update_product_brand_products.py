# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfImportUpdateProductBrandProducts(models.TransientModel):
    _name = 'of.import.update.product.brand.products'

    brand_id = fields.Many2one('of.product.brand', 'Marque', required=True)
    product_ids = fields.Many2many('product.template', string="Articles", domain="[('brand_id', '=', brand_id)]")

    @api.multi
    def update_products(self):
        self.ensure_one()
        products = self.product_ids or self.brand_id.product_ids
        products.of_action_update_from_brand()
        return True
