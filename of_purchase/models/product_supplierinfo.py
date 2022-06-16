# -*- coding: utf-8 -*-
from odoo import models, api


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.multi
    def write(self, vals):
        if 'price' in vals and len(self) == 1:
            price = vals['price']
            product_tmpl_id = vals.get('product_tmpl_id', self.product_tmpl_id.id)
            product_id = vals.get('product_id', self.product_id.id)
            products_done = self.env['product.product']

            if product_tmpl_id:
                product_tmpl = self.env['product.template'].browse(product_tmpl_id)
                if product_tmpl.seller_ids and product_tmpl.seller_ids[0].id == self.id:
                    product_tmpl.product_variant_ids.of_purchase_coeff_seller_price_propagation(price)
                    products_done |= product_tmpl.product_variant_ids

            if product_id and (not products_done or product_id not in products_done.ids):
                product = self.env['product.product'].browse(product_id)
                if product.seller_ids and product.seller_ids[0].id == self.id:
                    product.of_purchase_coeff_seller_price_propagation(price)
        return super(ProductSupplierinfo, self).write(vals)
