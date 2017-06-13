# -*- coding: utf-8 -*-

import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging

class OFKitAccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    contains_kit = fields.Boolean(string='Contains a kit', compute='_compute_contains_kit')
    
    @api.multi
    @api.depends('invoice_line_ids')
    def _compute_contains_kit(self):
        line_obj = self.env['account.invoice.line']
        for invoice in self:
            invoice.contains_kit = line_obj.search([("invoice_id", "=",invoice.id),('is_kit','=',True)],count=True) > 0


class OFKitAccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    is_kit = fields.Boolean(related='product_id.is_kit')
    component_ids = fields.One2many('account.invoice.line.comp', 'invoice_line_id', string='Components', domain=[('is_kit','=',False)])
    under_kit_ids = fields.One2many('account.invoice.line.comp', 'invoice_line_id', string='Under Kits', domain=[('is_kit','=',True)])
    
    unit_compo_price = fields.Monetary('Compo Price/Kit',digits=dp.get_precision('Product Price'),compute='_compute_unit_compo_price')
    
    pricing = fields.Selection([
        ('fixed','Fixed'),
        ('dynamic','Dynamic')
        ],string="Pricing type", help="fixed for all products that are not kits. Can be set to dynamic if product is a kit",
            related="product_id.pricing", required=True, default='fixed')
    
    @api.onchange('component_ids','under_kit_ids')
    def _compute_unit_compo_price(self):
        for line in self:
            if line.is_kit:
                price = 0
                for compo in line.component_ids:
                    price += compo.shown_price
                for under_kit in line.under_kit_ids:
                    price += under_kit.shown_price
                line.unit_compo_price = price
            #line._refresh_price_unit()
    
    @api.onchange('unit_compo_price')
    def _refresh_price_unit(self):
        for line in self:
            if line.is_kit:
                """price = 0
                for compo in line.component_ids:
                    price += compo.shown_price
                for under_kit in line.under_kit_ids:
                    price += under_kit.shown_price"""
                if line.pricing == 'dynamic':
                    line.price_unit = line.unit_compo_price


class OFKitAccountInvoiceLineComponent(models.Model):
    _name = 'account.invoice.line.comp'
    _description = 'Invoice Line Components'
    
    invoice_line_id = fields.Many2one('account.invoice.line',string='Invoice Line',ondelete='cascade',required=True,readonly=True)
    invoice_id = fields.Many2one('account.invoice', string='Invoice', related='invoice_line_id.invoice_id',readonly=True)
    bom_path = fields.Char(string='BoM Chain', readonly=True)
    
    product_id = fields.Many2one('product.product',string='Product',required=True,readonly=True)
    #product_tmpl_id = fields.Many2one('product.template',string='Product')
    is_kit = fields.Boolean(related='product_id.is_kit', help="True if this comp is a kit itself")
    rec_lvl = fields.Integer(string="Recursion Level", readonly=True, help="1 for components of a kit. 2 for components of a kit inside a kit... etc.")
    parent_id = fields.Many2one('account.invoice.line.comp',string='Parent Comp',readonly=True)
    child_ids = fields.One2many('account.invoice.line.comp', 'parent_id', string='Children Comps',readonly=True)
    
    pricing = fields.Selection([
        ('fixed','Fixed'),
        ('dynamic','Dynamic')
        ],string="Pricing type", help="fixed for all products that are not kits. Can be set to dynamic if product is a kit",
            required=True, default='fixed')
    
    currency_id = fields.Many2one(related='invoice_id.currency_id', store=True, string='Currency', readonly=True)
    product_uom = fields.Many2one('product.uom', string='UoM', required=True)
    unit_price = fields.Monetary('Unit Price',digits=dp.get_precision('Product Price'),readonly=True)
    unit_cost = fields.Monetary('Unit Cost',digits=dp.get_precision('Product Price'),readonly=True)
    
    unit_qty_under_kit = fields.Float(string='Qty per Underkit (An underkit is a kit inside a kit)', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    unit_qty = fields.Float(string='Qty per kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
                            help="Quantity per kit (eg. per invoice line)")
    nb_units = fields.Float(string='Number of kits', related='invoice_line_id.quantity', readonly=True, required=True)
    product_total_qty = fields.Float(string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, 
                                   compute='_compute_product_total_qty', help='total quantity equal to quantity per kit times number of kits')
    
    shown_price_total = fields.Monetary(string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), 
                                   compute='_compute_shown_price', help="Price equal to 0 if pricing of the kit is set to 'fixed'")
    shown_price = fields.Monetary(string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), 
                                   compute='_compute_shown_price', help="Price equal to 0 if pricing of the kit is set to 'fixed'")
    
    @api.depends('pricing','unit_qty','product_total_qty','parent_id.pricing')
    def _compute_shown_price(self):
        for comp in self:
            if comp.invoice_line_id.pricing == 'fixed' or (comp.is_kit and comp.pricing == 'dynamic') or (comp.parent_id and comp.parent_id.pricing == 'fixed'):
                comp.shown_price_total = 0.0
                comp.shown_price = 0.0
            else:
                comp.shown_price_total = comp.unit_price * comp.product_total_qty
                comp.shown_price = comp.unit_price * comp.unit_qty
    
    @api.depends('unit_qty','nb_units')
    def _compute_product_total_qty(self):
        for comp in self:
            comp.product_total_qty = comp.unit_qty * comp.nb_units 
            
    def find_parent(self):
        """ connect self to it's parent """
        self.ensure_one()
        if self.rec_lvl > 1:
            under_kits = self.env['account.invoice.line.comp'].search([('rec_lvl','=',self.rec_lvl -1),('is_kit','=',True)])
            if len(under_kits) == 1:
                self.parent_id = under_kits[0].id
            elif len(under_kits) > 1:
                parent_str = self.bom_path.split(' -> ')[self.rec_lvl - 1]
                for u_kit in under_kits:
                    if u_kit.product_id.product_tmpl_id.name == parent_str:
                        self.parent_id = u_kit.id
                        break
    
    
    
    
    