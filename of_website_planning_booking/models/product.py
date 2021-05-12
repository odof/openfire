# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OFProductBrand(models.Model):
    _inherit = 'of.product.brand'

    website_published = fields.Boolean(string=u"Publié sur le site internet", copy=False)

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        return self.write({'website_published': not self.website_published})


class ProductCategory(models.Model):
    _inherit = 'product.category'

    website_published = fields.Boolean(string=u"Publié sur le site internet", copy=False)

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        return self.write({'website_published': not self.website_published})
