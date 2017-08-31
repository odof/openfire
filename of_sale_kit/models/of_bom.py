# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.addons import decimal_precision as dp

class OFBom(models.Model):
    _inherit='mrp.bom'
    
    type = fields.Selection([
        ('normal', 'Manufacture this product'),
        ('phantom', 'This product is a kit')],# 'BoM Type',
        default='phantom',#, required=True,
        help="Kit (Phantom): When processing a sales order for this product, the delivery order will contain all the components that are not kits themselves. \
        (a kit itself can contain kits, sometimes called under-kits).")

    def get_components_price_old(self, rec_qty=1, without_pricing=True):
        """
        recursive method.
        returns the sum of the price of all components in this bom. 
        doesn't take 'pricing' into account unless without_pricing set to false.
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
                else: # the under-kit pricing is computed, we need the price of its components
                    res += line.child_bom_id.get_components_price(rec_qty*line.product_qty)
            else: # this line is not a bom
                res += line.product_id.lst_price  * line.product_qty * rec_qty
        return res

    def get_components_price(self, rec_qty=1, without_pricing=True):
        """
        recursive method.
        returns the sum of the price and cost of all components in this bom.
        doesn't take 'pricing' into account unless without_pricing set to false.
        """
        self.ensure_one()
        self._check_product_recursion()
        res = {'price': 0.0, 'cost': 0.0}
        for line in self.bom_line_ids:
            if line.child_bom_id: # this line is bom. Its product is a kit (or under-kit)
                if without_pricing: # we don't take kits pricing into account
                    tmp_res = line.child_bom_id.get_components_price(rec_qty*line.product_qty)
                    res['price'] += tmp_res['price']
                    res['cost'] += tmp_res['cost']
                elif line.product_id.pricing == 'fixed': # the under-kit pricing is fixed, its components price does not matter
                    res['cost'] += line.child_bom_id.get_components_price(rec_qty*line.product_qty)['cost']
                    res['price'] += line.product_id.lst_price * line.product_qty * rec_qty
                else: # the under-kit pricing is computed, we need the price of its components
                    tmp_res = line.child_bom_id.get_components_price(rec_qty*line.product_qty)
                    res['price'] += tmp_res['price']
                    res['cost'] += tmp_res['cost']
            else: # this line is not a bom
                res['price'] += line.product_id.lst_price  * line.product_qty * rec_qty
                res['cost'] += line.product_id.standard_price  * line.product_qty * rec_qty
        return res

    @api.multi
    def get_components(self, rec_lvl=0, parent_qty_per_line=1, parent_chain="", origin="sale"):
        self.ensure_one()
        self._check_product_recursion()
        res = []
        for line in self.bom_line_ids:
            comp_name = line.product_id.name_get()[0][1] or line.product_id.name
            comp = { 
                    'rec_lvl': rec_lvl+1,
                    'parent_chain': parent_chain ,
                    'product_id': line.product_id.id,
                    'name': comp_name,
                    'default_code': line.product_id.default_code,
                    'qty_per_line': line.product_qty * parent_qty_per_line,
                    'price_unit': line.product_id.lst_price,
                    'cost_unit': line.product_id.standard_price,
                }
            if line.child_bom_id and line.child_bom_id.type == 'phantom': # this line is a kit
                comp['pricing'] = 'computed'
                comp['is_kit'] = True
                if origin == 'sale':
                    comp['product_uom'] = line.product_uom_id.id
                elif origin == 'account':
                    comp['uom_id'] = line.product_uom_id.id
            else:
                comp['pricing'] = 'fixed'
                comp['is_kit'] = False
                if origin == 'sale':
                    comp['product_uom'] = line.product_uom_id.id
                elif origin == 'account':
                    comp['uom_id'] = line.product_uom_id.id
            res.append((0, 0, comp))
        return res

    @api.multi
    def get_components_rec(self, rec_lvl=1, parent_qty_per_line=1, parent_chain=""):
        """
        recursive method.
        returns a list of all components (and under-kits) in this bom
        to be reworked
        """
        self.ensure_one()
        self._check_product_recursion()
        res = []
        for line in self.bom_line_ids:
            if line.child_bom_id and line.child_bom_id.type == 'phantom': # this line is kit. get the components and add the under_kit

                under_comps = line.child_bom_id.get_components_rec(rec_lvl+1, parent_qty_per_line*line.product_qty, parent_chain + " -> " + line.product_id.name) # recursive call, get the components of the under_kit
                comp = { #under_kit
                    'rec_lvl': rec_lvl+1,
                    'parent_chain': parent_chain ,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'pricing': 'computed', # set pricing of under_kits to computed by default
                    'is_kit': True,
                    'qty_per_parent': line.product_qty,
                    'qty_per_line': parent_qty_per_line * line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'price_unit': line.product_id.lst_price,
                    'cost_unit': line.product_id.standard_price,
                    'child_ids': under_comps,
                }
            else:
                comp = {
                    'rec_lvl': rec_lvl+1,
                    'parent_chain': parent_chain,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'pricing': 'fixed',
                    'is_kit': False,
                    'qty_per_parent': line.product_qty, # the qty as it is given in the bom
                    'qty_per_line': parent_qty_per_line * line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'price_unit': line.product_id.lst_price,
                    'cost_unit': line.product_id.standard_price,
                }
            res.append((0, 0, comp))
        return res

    @api.onchange('type')
    def _onchange_type(self):
        # method to force product_qty to be 1 in case of kit. ATM Openfire Kits can't handle product_qty different than 1
        for bom in self:
            if bom.type == 'phantom':
                bom.product_qty = 1

    @api.model
    def create(self, vals):
        bom = super(OFBom, self).create(vals)
        # call to related product method. get around issues with store=True
        bom.product_tmpl_id._compute_is_kit()
        bom.product_tmpl_id._compute_current_bom_id()
        if bom.type == 'phantom':
            bom.product_tmpl_id.type = 'service' # kit products are services
            bom.product_tmpl_id.pricing = 'computed' # kit pricing is computed by default
            bom.product_tmpl_id.standard_price = bom.get_components_price(1, True)['cost']
        return bom

    @api.multi
    def write(self, vals):
        for bom in self:
            super(OFBom, bom).write(vals)
            if 'type' in vals:
                #call to related product method
                bom.product_tmpl_id._compute_is_kit()
                bom.product_tmpl_id._compute_current_bom_id()
                if vals['type'] == 'phantom':
                    bom.product_tmpl_id.type = 'service' # kit products are services
                    bom.product_tmpl_id.pricing = 'computed' # kits pricing is computed by default
            if 'bom_line_ids' in vals:
                bom.product_tmpl_id.standard_price = bom.get_components_price(1, True)['cost']
        return True
