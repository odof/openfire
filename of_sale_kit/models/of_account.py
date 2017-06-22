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
    
    components = fields.One2many('account.invoice.line.comp', 'invoice_id', string='Components', domain=[('is_kit_invoice_comp','=',False)], readonly=True,
                    help="Contains all components in this invoice that are not kits")
    
    @api.multi
    @api.depends('invoice_line_ids.product_id')
    def _compute_contains_kit(self):
        line_obj = self.env['account.invoice.line']
        for invoice in self:
            invoice.contains_kit = line_obj.search([("invoice_id", "=",invoice.id),('is_kit_invoice_line','=',True)],count=True) > 0

    kit_display_mode = fields.Selection([
        ('collapse','Collapse'),
        #('collapse_expand','One line per kit, with detail'),
        ('expand','Expand'),
        ], string='Kit display mode', default='expand',
            help="defines the way kits should be printed out in pdf reports:\n\
            - Collapse: One line per kit, with minimal info\n\
            - Expand: One line per kit, plus one line per component")


class OFKitAccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    direct_child_ids = fields.One2many('account.invoice.line.comp', 'invoice_line_id', string='Direct children', domain=[('parent_id','=',False)],
                            help="Contains all components that are direct children of this invoice line")
    is_kit_invoice_line = fields.Boolean(string='Is a kit')

    unit_compo_price = fields.Monetary('Compo Price/Kit',digits=dp.get_precision('Product Price'),compute='_compute_unit_compo_price',
                            help="Sum of the prices of all components necessary for 1 unit of this kit")
    
    pricing = fields.Selection([
        ('fixed','Fixed'),
        ('dynamic','Dynamic')
        ],string="Pricing type", required=True, default='fixed',
            help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'dynamic', the price will be computed according to the components of the kit.")

    def get_kit_descr_collapse(self):
        """
        returns a string to be added to a kit name in PDF reports when kit display mode is set to 'Collapse'
        that string contains all components in this line that are not kits, plus their total quantities
        """
        self.ensure_one()
        if not self.is_kit_invoice_line:
            return ""
        comp_obj = self.env['account.invoice.line.comp']
        components = comp_obj.search([('invoice_line_id','=',self.id),('is_kit_invoice_comp','=',False)]) # get all comps that are not kits
        ir_model_data = self.env['ir.model.data']
        units_id = ir_model_data.get_object_reference('product','product_uom_unit')[1]
        res = []
        for comp in components:
            qty_int_val = int(comp.qty_total)
            if comp.uom_id.id == units_id: # uom is units, no need to print it
                qty = str(qty_int_val) # qty is an int because it's in units
                comp_str = comp.name + ": " + qty
            else:
                if qty_int_val == comp.qty_total:
                    qty = str(qty_int_val)
                else:
                    qty = str(comp.qty_total)
                comp_str = comp.name + ": " + qty + " " + comp.uom_id.name
            res.append(comp_str)
        res = " (" + ", ".join(res) + ")"
        return res
    
    def get_all_comps(self,only_leaves=False):
        """
        Function used when printing out PDF reports in Expand mode.
        returns all components in this invoice line, in correct order (children components directly under their parent)
        """
        def get_comp_comps(comp):
            if not comp.is_kit_invoice_comp:
                return [comp] # stop condition
            if only_leaves: # meaning we don't want under-kits
                res = []
            else:
                res = [comp]
            for c in comp.child_ids:
                res += get_comp_comps(c) # recursive call
            return res
        self.ensure_one()
        if not self.is_kit_invoice_line:
            return []
        result = []
        for comp in self.direct_child_ids:
            result += get_comp_comps(comp)
        return result
        
    @api.onchange('quantity','uom_id')
    def _onchange_uom_id(self):
        self.ensure_one()
        super(OFKitAccountInvoiceLine,self)._onchange_uom_id()
        self._refresh_price_unit()
    
    @api.multi
    @api.onchange('product_id')
    def _onchange_product_id(self):
        super(OFKitAccountInvoiceLine,self)._onchange_product_id()
        new_vals = {}
        if self.is_kit_invoice_line: # former product was a kit, we need to delete its components
            self.direct_child_ids = [(5,)]
        if self.product_id.is_kit: # new product is a kit, we need to add its components
            new_vals['is_kit_invoice_line'] = True
            new_vals['pricing'] = self.product_id.pricing or 'dynamic'
            bom_obj = self.env['mrp.bom']
            bom = bom_obj.search([('product_id','=',self.product_id.id)], limit=1)
            if not bom:
                product_tmpl_id = self.product_id.product_tmpl_id
                bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
            if bom:
                comp_name = self.product_id.name_get()[0][1] or self.product_id.name
                components = bom.get_components(0,1,comp_name,'account')
                if new_vals['pricing'] == 'fixed':
                    for comp in components:
                        comp[2]['hide_prices'] = True
                new_vals['direct_child_ids'] = components
        else: # new product is not a kit
            new_vals['is_kit_invoice_line'] = False
            new_vals['pricing'] = 'fixed'
        self.update(new_vals)
    
    @api.depends('direct_child_ids')
    def _compute_unit_compo_price(self):
        for line in self:
            if line.is_kit_invoice_line:
                uc_price = 0
                for comp in line.direct_child_ids:
                    uc_price += comp.price_per_line
                line.unit_compo_price = uc_price
                line._refresh_price_unit()
    
    @api.onchange('unit_compo_price','quantity','pricing')
    def _refresh_price_unit(self):
        for line in self:
            if line.is_kit_invoice_line:
                if line.pricing == 'dynamic':
                    line.price_unit = line.unit_compo_price
                else:
                    line.price_unit = line.product_id.list_price

    @api.onchange('is_kit_invoice_line')
    def _onchange_is_kit_invoice_line(self):
        if self.is_kit_invoice_line:
            if not self.product_id.is_kit: # a product that is not a kit is being made into a kit
                # we create a component with current product (for procurements, kits are ignored)
                comp_name = self.product_id.name_get()[0][1] or self.product_id.name
                new_comp_vals = {
                    'product_id': self.product_id.id,
                    'rec_lvl': 1,
                    'name': comp_name,
                    'bom_path': comp_name,
                    'is_kit_invoice_comp': False,
                    'qty_per_parent': 1,
                    #'qty_per_line': 1,
                    'uom_id': self.uom_id,
                    'price_unit': self.product_id.list_price,
                    'unit_cost': self.product_id.standard_price,
                    }
                
                self.update({
                    'direct_child_ids': [(0,0,new_comp_vals)],
                    'pricing': 'dynamic',
                    'price_unit': self.unit_compo_price,
                    })
            else:
                pass
        else: # a product that was a kit is not anymore, we unlink its components
            self.update({
                'direct_child_ids': [(5,)],
                })

    @api.multi
    def _init_components(self):
        """
        Create records in 'account.invoice.line.comp' for each component of a kit that have not yet been loaded.
        """
        for line in self:
            if line.is_kit_invoice_line:
                comp_obj = line.env['account.invoice.line.comp'].search([('invoice_line_id','=',self.id),('children_loaded','=',False)])
                if line.pricing == 'dynamic':
                    hide_prices = False
                else:
                    hide_prices = True 
                for comp in comp_obj:
                    comp.load_under_components(True,hide_prices)

    def init_comps_from_so_line(self, so_line_id):
        # called by sale.order.line.invoice_line_create
        self.ensure_one()
        so_line = self.env['sale.order.line'].search([('id','=',so_line_id)])
        if self.is_kit_invoice_line:
            direct_children = []
            for comp in so_line.direct_child_ids:
                direct_children += comp._prepare_invoice_line_comp(self.id)
            self.direct_child_ids = direct_children
            self._init_components()
            self._refresh_price_unit()

    @api.model
    def create(self, vals):
        # from_so_line key added in vals in case of creation from a sale order
        from_so_line = vals.pop("from_so_line",False)
        
        line = super(OFKitAccountInvoiceLine,self).create(vals)
        if line.is_kit_invoice_line and not from_so_line:
            line._init_components()
            if line.pricing == 'dynamic':
                line.price_unit = line.unit_compo_price
            #line._refresh_price_unit()
        return line
    
    @api.multi
    def write(self,vals):
        if len(self._ids) == 1 and self.pricing == 'dynamic' and not self.price_unit == self.unit_compo_price:
            vals['price_unit'] = self.unit_compo_price
        super(OFKitAccountInvoiceLine,self).write(vals)
        if 'product_id' in vals:
            self._init_components()
        if 'pricing' in vals: # it is not possible to do it on the fly for some reason
            if vals['pricing'] == 'dynamic':
                self.direct_child_ids.toggle_hide_prices(False,True)
            if vals['pricing'] == 'fixed':
                self.direct_child_ids.toggle_hide_prices(True,True)
        return True

class OFKitAccountInvoiceLineComponent(models.Model):
    _name = 'account.invoice.line.comp'
    _description = 'Invoice Line Components'
    _order = 'bom_path'
    
    invoice_line_id = fields.Many2one('account.invoice.line',string='Invoice Line',ondelete='cascade',required=True,readonly=True)
    invoice_id = fields.Many2one('account.invoice', string='Invoice', related='invoice_line_id.invoice_id', readonly=True)
    bom_path = fields.Char(string='Kit Arch',help="Contains the chain of parents of this component")
    order_comp_id = fields.Many2one('sale.order.line.comp',string="Sale Order Component")
    
    name = fields.Char(string='Name',required=True)
    
    product_id = fields.Many2one('product.product',string='Product',required=True)
    is_kit_invoice_comp = fields.Boolean(string="Is a kit",required=True, default=False,
                            help="True if this comp is a kit itself. Also called an under-kit in that case")
    rec_lvl = fields.Integer(string="Recursion Level", readonly=True, help="1 for components of a kit. 2 for components of a kit inside a kit... etc.")
    parent_id = fields.Many2one('account.invoice.line.comp',string='Parent Comp', ondelete='cascade')
    child_ids = fields.One2many('account.invoice.line.comp', 'parent_id', string='Children Comps')
    load_children = fields.Boolean(string="Load children",
                        help="odoo is currently unable to load components of components at once on the fly. \n \
                        check this box to load this component under-components on the fly. \n \
                        if you don't, all components will be loaded when you click 'save' on the invoice.")
    children_loaded = fields.Boolean(string="Children loaded") # no readonly for this or bug double children loading
    
    pricing = fields.Selection([
        ('fixed','Fixed'),
        ('dynamic','Dynamic')
        ],string="Pricing", required=True, default='fixed',
            help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'dynamic', the price will be computed according to the components of the kit.")
    currency_id = fields.Many2one(related='invoice_id.currency_id', store=True, string='Currency', readonly=True)
    uom_id = fields.Many2one('product.uom', string='UoM', required=True)
    price_unit = fields.Monetary('Unit Price',digits=dp.get_precision('Product Price'),required=True,default=0.0,oldname="unit_price")
    children_price = fields.Monetary('Unit Price',digits=dp.get_precision('Product Price'),compute='_compute_prices')
    unit_cost = fields.Monetary('Unit Cost',digits=dp.get_precision('Product Price'))
    
    qty_per_parent = fields.Float(string='Qty / parent', digits=dp.get_precision('Product Unit of Measure'),oldname='qty_bom_line',
                        help="Quantity per direct parent unit.")
    qty_per_line = fields.Float(string='Qty / Invline', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
                            help="Quantity per invoice line kit unit", compute="_compute_qty_per_line",oldname="qty_inv_line")

    nb_units = fields.Float(string='Number of kits', related='invoice_line_id.quantity', readonly=True)
    qty_total = fields.Float(string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), 
                                   compute='_compute_qty_total', help='total quantity equal to quantity per kit times number of kits')
    display_qty_changed = fields.Boolean(string="display qty changed message",default=False)
    price_total = fields.Monetary(string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
                            help="Equal to total quantity * unit price", oldname="shown_price_total")
    price_per_line = fields.Monetary(string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
                            help="Equal to quantity per so line unit * unit price", oldname="shown_price")

    hide_prices = fields.Boolean(string="Hide prices", default=False)
    
    """
    state = fields.Selection([
        ('draft','Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], related='invoice_id.state', string='Invoice Status', readonly=True, copy=False, store=True, default='draft')"""
    
    @api.multi
    def toggle_hide_prices(self,hide,rec=True):
        for comp in self:
            if hide:
                comp.hide_prices =  True
            else:
                comp.hide_prices = False
            if comp.child_ids and rec:
                comp.child_ids.toggle_hide_prices(hide)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.is_kit_invoice_comp:
            # former product was a kit, lets clear its components
            self.update({
                'child_ids': [(5,)],
                'children_loaded': False,
            })
        
        new_vals = {
            'name': self.product_id.name_get()[0][1] or self.product_id.name,
            'pricing': self.product_id.pricing or 'fixed',
            'uom_id': self.product_id.product_tmpl_id.uom_id,
            'price_unit': self.product_id.list_price,
            'unit_cost': self.product_id.standard_price,
            'qty_per_parent': 1,
            }
        if self.parent_id:
            if not self.bom_path:
                bom_path = self.parent_id.bom_path + " -> " + self.parent_id.name
            else:
                bom_path = self.bom_path
            hide_prices = self.parent_id.hide_prices
            rec_lvl = self.parent_id.rec_lvl +1
            qty_per_line_parent = self.parent_id.qty_per_line
        else:
            if not self.bom_path: # on creation, when choosing a product
                bom_path = self.invoice_line_id.name
            else:
                bom_path = self.bom_path
            if self.invoice_line_id:
                if self.invoice_line_id.pricing == 'fixed':
                    hide_prices = True
                else:
                    hide_prices = False
            else:
                hide_prices = False
            rec_lvl = 1
            qty_per_line_parent = 1
        if self.product_id:
            comp_name = self.product_id.name_get()[0][1] or self.product_id.name
            new_vals['name'] = comp_name
        #new_vals['qty_per_line'] = qty_per_line_parent
        new_vals['bom_path'] = bom_path
        new_vals['rec_lvl'] = rec_lvl
        new_vals['hide_prices'] = hide_prices
        
        if self.product_id.is_kit:
            # new product is a kit, lets add its components
            new_vals['is_kit_invoice_comp'] = True
            new_vals['pricing'] = 'dynamic'
            bom_obj = self.env['mrp.bom']
            bom = bom_obj.search([('product_id','=',self.product_id.id)], limit=1)
            if not bom:
                product_tmpl_id = self.product_id.product_tmpl_id
                bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
            if bom:
                comp_name = self.product_id.name_get()[0][1] or self.product_id.name
                under_components = bom.get_components(rec_lvl,qty_per_line_parent,bom_path + " -> " + comp_name,'account')
                if hide_prices:
                    for under_comp in under_components:
                        under_comp[2]['hide_prices'] = True
                new_vals['child_ids'] = under_components
                new_vals['children_loaded'] = True
        else:
            # le nouveau produit n'est pas un kit
            new_vals['is_kit_invoice_comp'] = False
            new_vals['pricing'] = 'fixed'
        
        self.update(new_vals)
    
    @api.onchange('qty_per_parent')
    def _onchange_qty_per_parent(self):
        if self.is_kit_invoice_comp:
            self.display_qty_changed = True

    @api.onchange('load_children')
    def _onchange_load_children(self):
        """
        checkbox to load components on the fly before saving. Odoo doesn't handle well recursive one2many on the fly
        """
        if self.load_children:
            self.load_under_components(False,self.hide_prices)
    
    @api.multi
    def load_under_components(self,recursive=False,hide_prices=False):
        #TODO: optimiser le cas recursif par appel à get_components_rec?
        for comp in self:
            if comp.is_kit_invoice_comp and not comp.children_loaded:
                bom_obj = self.env['mrp.bom']
                bom = bom_obj.search([('product_id','=',comp.product_id.id)], limit=1)
                if not bom:
                    product_tmpl_id = comp.product_id.product_tmpl_id
                    bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
                if bom:
                    comp_name = comp.product_id.name_get()[0][1] or comp.product_id.name
                    components = bom.get_components(comp.rec_lvl,comp.qty_per_line,comp.bom_path + " -> " + comp_name,'account')
                    if hide_prices:
                        for under_comp in components:
                            under_comp[2]['hide_prices'] = True
                    comp.child_ids = components
                comp.children_loaded = True
                if recursive:
                    comp.child_ids.load_under_components(True,hide_prices)
            else:
                comp.hide_prices = hide_prices
    
    @api.depends('child_ids','qty_per_line','nb_units')
    def _compute_prices(self):
        for comp in self:
            qty_per_line = comp.qty_per_line
            if comp.is_kit_invoice_comp:
                children_price = comp.child_ids.get_prices_rec(1)
                comp.children_price = children_price # unit price
                comp.price_per_line = children_price * qty_per_line
                comp.price_total = children_price * qty_per_line * comp.nb_units
            else:
                comp.children_price = comp.price_unit
                comp.price_per_line = comp.price_unit * qty_per_line
                comp.price_total = comp.price_unit * qty_per_line * comp.nb_units

    @api.multi
    def get_prices_rec(self,qty_parent=1):
        """
        returns the price of the components in self and their children.
        doesn't take under-kits pricing into account.
        :param qty_parent: 
        """
        res = 0
        for comp in self:
            if not comp.is_kit_invoice_comp: # comp is not a kit, stop condition
                res += comp.price_unit * comp.qty_per_parent * qty_parent
            else:
                res += comp.child_ids.get_prices_rec(qty_parent * comp.qty_per_parent) # recursive call
                if not comp.children_loaded:
                    bom_obj = self.env['mrp.bom']
                    bom = bom_obj.search([('product_id','=',comp.product_id.id)], limit=1)
                    if not bom:
                        product_tmpl_id = comp.product_id.product_tmpl_id
                        bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
                    if bom:
                        res += bom.get_components_price(comp.qty_per_line,True)
        return res

    @api.depends('qty_per_parent','parent_id')
    def _compute_qty_per_line(self):
        for comp in self:
            parent = comp.parent_id
            qty = comp.qty_per_parent
            while parent:
                qty *= parent.qty_per_parent
                parent = parent.parent_id
            comp.qty_per_line = qty
    
    @api.depends('qty_per_line','nb_units')
    def _compute_qty_total(self):
        for comp in self:
            comp.qty_total = comp.qty_per_line * comp.nb_units 

    @api.model
    def create(self, vals):
        if vals.get('parent_id') and not vals.get('invoice_line_id'):
            vals['invoice_line_id'] = self.browse(vals['parent_id']).invoice_line_id.id
        comp = super(OFKitAccountInvoiceLineComponent,self).create(vals)
        if not comp.bom_path:
            comp.bom_path = comp.invoice_line_id.name
        return comp
    
    @api.multi
    def write(self,vals):
        super(OFKitAccountInvoiceLineComponent,self).write(vals)
        for comp in self:
            if comp.display_qty_changed:
                # set to True in onchange_qty_per_parent, we need to set it back to False so the message doesn't stay
                comp.display_qty_changed = False
        return True
    