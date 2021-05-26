# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PoductTemplate(models.Model):
    _inherit = 'product.template'

    of_worktop_configurator_accessory = fields.Boolean(string=u"Accessoire calculateur")


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', 'pricelist_id',
                 'percent_price', 'price_discount', 'price_surcharge', 'of_brand_id', 'of_coef')
    def _get_pricelist_item_name_price(self):
        super(ProductPricelistItem, self)._get_pricelist_item_name_price()
        if self.compute_price == 'coef':
            self.price = "Coefficient : %s" % int(self.of_coef * 100.0)
