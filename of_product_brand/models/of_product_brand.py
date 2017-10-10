# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class OfProductBrand(models.Model):
    _name = 'of.product.brand'

    name = fields.Char('Name')
    prefix = fields.Char('Prefix')
    partner_id = fields.Many2one('res.partner', string='Supplier')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one(string='Brand', related='product_variant_ids.brand_id')
#     # related to display product product information if is_product_variant
#     barcode = fields.Char('Barcode', oldname='ean13', related='product_variant_ids.barcode')
#     default_code = fields.Char(
#         'Internal Reference', compute='_compute_default_code',
#         inverse='_set_default_code', store=True)
# 
#     @api.depends('product_variant_ids', 'product_variant_ids.default_code')
#     def _compute_default_code(self):
#         unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
#         for template in unique_variants:
#             template.default_code = template.product_variant_ids.default_code
#         for template in (self - unique_variants):
#             template.default_code = ''
# 
#     @api.one
#     def _set_default_code(self):
#         if len(self.product_variant_ids) == 1:
#             self.product_variant_ids.default_code = self.default_code


class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand_id = fields.Many2one('of.product.brand', compute='_compute_brand_id', inverse='_inverse_brand_id', store=True)

    @api.multi
    @api.depends('default_code', 'brand_id.prefix')
    def _compute_brand_id(self):
        # A product brand is given by its reference prefix
        brand_obj = self.env['of.product.brand']
        brands = brand_obj.search([])
        brands = {brand.prefix: brand for brand in brands}
        for product in self:
            prefix = (product.default_code or '').split('_')[0]
            product.brand_id = brands.get(prefix, False)

    def _inverse_brand_id(self):
        for product in self:
            code = product.default_code
            ind = code.find('_')
            prefix = ind < 0 and code[:ind]
            if ind > 0:
                code = code[ind+1:]

            if product.brand:
                if product.brand.prefix != prefix:
                    product.reference = product.brand.prefix + "_" + code
            elif prefix:
                product.reference = code

class Partner(models.Model):
    _inherit = 'res.partner'

    brand_ids = fields.One2many('of.product.brand', 'partner_id', string="Brands")
    supplier_brand_count = fields.Integer(compute='_compute_supplier_brand_count', string='# Brands')

    @api.multi
    @api.depends('brand_ids')
    def _compute_supplier_brand_count(self):
        for partner in self:
            partner.supplier_brand_count = len(partner.brand_ids)
