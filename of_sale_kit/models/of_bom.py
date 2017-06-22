# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class OFBom(models.Model):
    _inherit='mrp.bom'
    
    def get_components_price(self,rec_qty=1,without_pricing=True):
        """
        recursive method.
        returns the sum of the price of all components in this bom. the return price of under-kits is function of their pricing.
        """
        self.ensure_one()
        self._check_product_recursion()
        res = 0.0
        for line in self.bom_line_ids:
            if line.child_bom_id: # this line is bom. Its product is a kit (or under-kit)
                if without_pricing: # we don't take kits pricing into account
                    res += line.child_bom_id.get_components_price(rec_qty*line.product_qty)
                elif line.product_id.pricing == 'fixed': # the under-kit pricing is fixed, its components price does not matter
                    res += line.product_id.lst_price * line.product_qty * rec_qty
                else: # the under-kit pricing is dynamic, we need the price of its components
                    res += line.child_bom_id.get_components_price(rec_qty*line.product_qty)
            else: # this line is not a bom
                res += line.product_id.lst_price  * line.product_qty * rec_qty
        return res
    
    @api.multi
    def get_components(self,rec_lvl=0,parent_qty_per_line=1,bom_path="",origin="sale"):
        self.ensure_one()
        self._check_product_recursion()
        res = []
        for line in self.bom_line_ids:
            comp_name = line.product_id.name_get()[0][1] or line.product_id.name
            comp = { 
                    'rec_lvl': rec_lvl+1,
                    'bom_path': bom_path ,
                    'product_id': line.product_id.id,
                    'name': comp_name,
                    #'pricing': 'dynamic', # set pricing of under_kits to dynamic by default
                    #'is_kit_order_comp': True,
                    'qty_per_parent': line.product_qty,
                    #'qty_per_line': parent_qty_per_line * line.product_qty,
                    #'product_uom': line.product_uom_id.id,
                    'price_unit': line.product_id.lst_price,
                    'unit_cost': line.product_id.standard_price,
                    #'child_ids': under_comps,
                }
            if line.child_bom_id and line.child_bom_id.type == 'phantom': # this line is a kit
                comp['pricing'] = 'dynamic'
                if origin == 'sale':
                    comp['product_uom'] = line.product_uom_id.id,
                    comp['is_kit_order_comp'] = True
                elif origin == 'account':
                    comp['uom_id'] = line.product_uom_id.id,
                    comp['is_kit_invoice_comp'] = True
            else:
                comp['pricing'] = 'fixed'
                if origin == 'sale':
                    comp['product_uom'] = line.product_uom_id.id,
                    comp['is_kit_order_comp'] = False
                elif origin == 'account':
                    comp['uom_id'] = line.product_uom_id.id,
                    comp['is_kit_invoice_comp'] = False
            res.append((0,0,comp))
        return res
    
    @api.multi
    def get_components_rec(self,rec_lvl=1,parent_qty_per_line=1,bom_path=""):
        """
        recursive method.
        returns a list of all components (and under-kits) in this bom
        """
        self.ensure_one()
        self._check_product_recursion()
        res = []
        for line in self.bom_line_ids:
            if line.child_bom_id and line.child_bom_id.type == 'phantom': # this line is kit. get the components and add the under_kit
                
                under_comps = line.child_bom_id.get_components_rec(rec_lvl+1, parent_qty_per_line*line.product_qty, bom_path + " -> " + line.product_id.name) # recursive call, get the components of the under_kit
                
                comp = { #under_kit
                    'rec_lvl': rec_lvl+1,
                    'bom_path': bom_path ,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'pricing': 'dynamic', # set pricing of under_kits to dynamic by default
                    'is_kit_order_comp': True,
                    'qty_per_parent': line.product_qty,
                    'qty_per_line': parent_qty_per_line * line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'price_unit': line.product_id.lst_price,
                    'unit_cost': line.product_id.standard_price,
                    'child_ids': under_comps,
                }
                
            else:
                    
                comp = {
                    'rec_lvl': rec_lvl+1,
                    'bom_path': bom_path,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'pricing': 'fixed',
                    'is_kit_order_comp': False,
                    'qty_per_parent': line.product_qty, # the qty as it is given in the bom
                    'qty_per_line': parent_qty_per_line * line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'price_unit': line.product_id.lst_price,
                    'unit_cost': line.product_id.standard_price,
#                    'children': [],
                }
            res.append((0,0,comp))
        #print res
        return res
    
    @api.model
    def create(self, vals):
        bom = super(OFBom,self).create(vals)
        #call to related product method
        bom.product_tmpl_id._compute_is_kit()
        bom.product_tmpl_id._compute_current_bom_id()
        if bom.type == 'phantom':
            bom.product_tmpl_id.type = 'service' # kit products are services
            bom.product_tmpl_id.pricing = 'dynamic' # kits pricing is dynamic by default
        return bom
    
    @api.multi
    def write(self, vals):
        for bom in self:
            super(OFBom,bom).write(vals)
            if 'type' in vals:
                #call to related product method
                bom.product_tmpl_id._compute_is_kit()
                bom.product_tmpl_id._compute_current_bom_id()
                if vals['type'] == 'phantom':
                    bom.product_tmpl_id.type = 'service' # kit products are services
                    bom.product_tmpl_id.pricing = 'dynamic' # kits pricing is dynamic by default
        return True
    