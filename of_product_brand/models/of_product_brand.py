# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfProductBrand(models.Model):
    _name = 'of.product.brand'

    name = fields.Char(string='Name', required=True)
    prefix = fields.Char(string='Prefix', required=True)
    partner_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier', '=', True)], required=True)
    product_ids = fields.One2many('product.template', 'brand_id', string='Products', readonly=True)
    product_variant_ids = fields.One2many('product.product', 'brand_id', string='Product variants', readonly=True)
    active = fields.Boolean(string='Active', default=True)
    logo = fields.Binary(string='Logo')
    product_count = fields.Integer(
        '# Products', compute='_compute_product_count',
        help="The number of products of this brand")
    note = fields.Text(string='Notes')

    def _compute_product_count(self):
        read_group_res = self.env['product.template'].read_group([('brand_id', 'in', self.ids)], ['brand_id'], ['brand_id'])
        group_data = dict((data['brand_id'][0], data['brand_id_count']) for data in read_group_res)
        for categ in self:
            categ.product_count = group_data.get(categ.id, 0)

    _sql_constraints = [
        ('prefix', 'unique(prefix)', "Another brand already exists with this prefix"),
    ]

    @api.model
    def create(self, vals):
        res = super(OfProductBrand, self).create(vals)
        products = self.env['product.product'].search([('default_code', '=like', vals['prefix'] + r'\_%')])
        products.write({'brand_id': res.id})
        return res

    @api.multi
    def write(self, vals):
        if len(self._ids) == 1:
            new_self = self.with_context(active_test=False)
            if 'prefix' in vals:
                # Reset products link to this brand
                new_products = new_self.env['product.product'].search([('default_code', '=like', vals['prefix'] + r'\_%')])
                vals['product_variant_ids'] = [(6, 0, list(new_products._ids))]
        return super(OfProductBrand, self).write(vals)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('of.product.brand', string='Brand', required=True)

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        # Ajout du préfixe de la marque sur l'article
        default_code = self.default_code or ''
        ind = default_code.find('_')
        prefix = self.brand_id and self.brand_id.prefix + '_' or ''
        default_code = prefix + default_code[ind+1:]
        if self.default_code != default_code:
            self.default_code = default_code

        # Création de la relation fournisseur
        if self.brand_id and not self.seller_ids:
            seller_data = {
                'name': self.brand_id.partner_id.id,
            }
            seller_data = self.env['product.supplierinfo']._add_missing_default_values(seller_data)
            self.seller_ids = [(0, 0, seller_data)]

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if self.default_code:
            ind = self.default_code.find('_')
            prefix = self.default_code[:ind]
            brand = self.env['of.product.brand'].search([('prefix', '=', prefix)])
            if brand != self.brand_id:
                self.brand_id = brand

    @api.model
    def create(self, vals):
        # Code copié depuis le module product
        # Permet l'attribution de la marque à la création de l'article

        # La marque est un champ obligatoire, qui doit donc être renseigné avant la création de l'article
        self = self.with_context(default_brand_id=vals.get('brand_id', False))
        template = super(ProductTemplate, self).create(vals)

        # This is needed to set given values to first variant after creation
        related_vals = {}
        if vals.get('brand_id') and template.brand_id.id != vals['brand_id']:
            related_vals['brand_id'] = vals['brand_id']
        if related_vals:
            template.write(related_vals)
        return template

class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand_id = fields.Many2one('of.product.brand', string='Brand', related='product_tmpl_id.brand_id', store=True, required=True)
    # @todo: Make it work with variants

class Partner(models.Model):
    _inherit = 'res.partner'

    brand_ids = fields.One2many('of.product.brand', 'partner_id', string="Brands")
    supplier_brand_count = fields.Integer(compute='_compute_supplier_brand_count', string='# Brands')

    @api.multi
    @api.depends('brand_ids')
    def _compute_supplier_brand_count(self):
        for partner in self:
            partner.supplier_brand_count = len(partner.brand_ids)
