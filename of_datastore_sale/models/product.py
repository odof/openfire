# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        super(ProductTemplate, self)._onchange_brand_id()
        if self.brand_id and self.brand_id.allow_dropshipping:
            route = self.env.ref('stock_dropshipping.route_drop_shipping', raise_if_not_found=False)
            self.route_ids |= route


class OFProductBrand(models.Model):
    _inherit = 'of.product.brand'

    allow_dropshipping = fields.Boolean(string="Livraison directe")

    @api.model
    def dropshipping_allowed(self):
        return self.env.user.has_group('of_datastore_sale.of_group_datastore_brand_dropshipping')

    @api.multi
    def write(self, vals):
        route = self.env.ref('stock_dropshipping.route_drop_shipping', raise_if_not_found=False)
        res = super(OFProductBrand, self).write(vals)
        if route and vals.get('allow_dropshipping'):
            self.mapped('product_ids').write({'route_ids': [(4, route.id)]})
        return res
