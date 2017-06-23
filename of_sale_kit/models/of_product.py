# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class OFKitProductTemplate(models.Model):
    _inherit = "product.template"
    
    is_kit = fields.Boolean(string="Is a kit", compute='_compute_is_kit', store=True)
    
    current_bom_id = fields.Many2one('mrp.bom', string="Current BoM", compute='_compute_current_bom_id', store=True)
    price_compo = fields.Monetary('Compo Price/Kit',digits=dp.get_precision('Product Price'),compute='_compute_price_compo',oldname="unit_compo_price")
    
    price_used = fields.Monetary('Used Price',digits=dp.get_precision('Product Price'),compute='_compute_price_used',oldname="used_price")
    
    pricing = fields.Selection([
        ('fixed','Fixed'),
        ('dynamic','Dynamic')
        ],string="Pricing type", required=True, default='fixed',
            help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'dynamic', the price will be computed according to the components of the kit.")
    
    @api.depends('bom_count')
    def _compute_is_kit(self):
        #this method will be called upon creation or change of a BoM for its related product (workaround store=True)
        read_group_res = self.env['mrp.bom'].read_group([('product_tmpl_id', 'in', self.ids),('type','=','phantom')], ['product_tmpl_id'], ['product_tmpl_id'])
        mapped_data = dict([(data['product_tmpl_id'][0], data['product_tmpl_id_count']) for data in read_group_res])
        for product in self:
            product.is_kit = mapped_data.get(product.id, 0) > 0
    
    @api.depends('bom_count')
    def _compute_current_bom_id(self):
        # this method will be called upon creation or change of a BoM for its related product (workaround store=True)
        if self.is_kit:
            boms = self.env['mrp.bom'].search([('product_tmpl_id', 'in', self.ids),('type','=','phantom')])
            if len(boms) == 1:
                bom = boms[0]
                #print bom
                self.current_bom_id = bom['id']
            elif len(boms) > 1:
                bom = boms[0] # meant to change later
                self.current_bom_id = bom['id']
        
    
    @api.depends('current_bom_id')
    def _compute_price_compo(self):
        for product in self:
            if product.is_kit:
                product.price_compo = product.current_bom_id.get_components_price(1,True)
    
    @api.depends('price_compo','pricing')
    def _compute_price_used(self):
        for product in self:
            if product.is_kit:
                if product.pricing == 'fixed':
                    product.price_used = product.list_price
                else:
                    product.price_used = product.price_compo

class OFKitProductProduct(models.Model):
    _inherit = "product.product"

    is_kit = fields.Boolean(related='product_tmpl_id.is_kit')
    
    pricing = fields.Selection([
        ('fixed','Fixed pricing'),
        ('dynamic','Pricing dependant of items actually in the kit')
        ],string="Pricing type", related="product_tmpl_id.pricing", required=True, default='fixed', store=True,
            help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'dynamic', the price will be computed according to the components of the kit.")

    
    
    
    
