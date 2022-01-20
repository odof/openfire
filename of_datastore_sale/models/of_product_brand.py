# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfProductBrand(models.Model):
    _inherit = 'of.product.brand'

    allow_dropshipping = fields.Boolean(string="Livraison directe")

    @api.model
    def dropshipping_allowed(self):
        return self.env.user.has_group('of_datastore_sale.of_group_datastore_brand_dropshipping')
