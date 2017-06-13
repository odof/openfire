# -*- coding: utf-8 -*-

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp

class OFKitSaleOrder(models.Model):
	_inherit = 'sale.order'
	
	contains_kit = fields.Boolean(string='Contains a kit', compute='_compute_contains_kit')
	
	components = fields.One2many('sale.order.line.comp', 'order_id', string='Components', domain=[('is_kit_order_comp','=',False)], readonly=True,
					help="Contains all components in this sale order that are not kits")
	
	@api.multi
	@api.depends('order_line.product_id')
	def _compute_contains_kit(self):
		line_obj = self.env['sale.order.line']
		for order in self:
			order.contains_kit = line_obj.search([("order_id", "=",order.id),('is_kit_order_line','=',True)],count=True) > 0

	kit_display_mode = fields.Selection([
		('collapse','Collapse'),
		#('collapse_expand','One line per kit, with detail'),
		('expand','Expand'),
		], string='kit display mode', default='expand',
			help="defines the way kits should be printed out in pdf reports:\n\
			- Collapse: One line per kit, with minimal info\n\
			- Expand: One line per component")

class OFKitSaleOrderLine(models.Model):
	_inherit = 'sale.order.line'
	
	direct_child_ids = fields.One2many('sale.order.line.comp', 'order_line_id', string='Direct children', domain=[('parent_id','=',False)],
							help="Contains all components that are direct children of this order line")
	is_kit_order_line = fields.Boolean(string='Is a kit')

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
		if not self.is_kit_order_line:
			return ""
		comp_obj = self.env['sale.order.line.comp']
		components = comp_obj.search([('order_line_id','=',self.id),('is_kit_order_comp','=',False)]) # get all comps that are not kits
		ir_model_data = self.env['ir.model.data']
		units_id = ir_model_data.get_object_reference('product','product_uom_unit')[1]
		res = []
		for comp in components:
			qty_int_val = int(comp.qty_total)
			if comp.product_uom.id == units_id: # uom is units, no need to print it
				qty = str(qty_int_val) # qty is an int because it's in units
				comp_str = comp.name + ": " + qty
			else:
				if qty_int_val == comp.qty_total:
					qty = str(qty_int_val)
				else:
					qty = str(comp.qty_total)
				comp_str = comp.name + ": " + qty + " " + comp.product_uom.name
			res.append(comp_str)
		res = " (" + ", ".join(res) + ")"
		return res
	
	def get_all_comps(self):
		"""
		returns all components in this order line, in correct order (children components directly under their parent)
		"""
		def get_comp_comps(comp):
			if not comp.is_kit_order_comp:
				return [comp] # stop condition
			res = [comp]
			for c in comp.child_ids:
				res += get_comp_comps(c) # recursive call
			return res
		self.ensure_one()
		if not self.is_kit_order_line:
			return []
		result = []
		for comp in self.direct_child_ids:
			result += get_comp_comps(comp)
		return result
		
	@api.onchange('product_uom_qty','product_uom')
	def product_uom_change(self):
		self.ensure_one()
		super(OFKitSaleOrderLine,self).product_uom_change()
		self._refresh_price_unit()
	
	@api.multi
	@api.onchange('product_id')
	def product_id_change(self):
		super(OFKitSaleOrderLine,self).product_id_change()
		new_vals = {}
		if self.is_kit_order_line: # former product was a kit, we need to delete its components
			self.direct_child_ids = [(5,)]
		if self.product_id.is_kit: # new product is a kit, we need to add its components
			new_vals['is_kit_order_line'] = True
			new_vals['pricing'] = self.product_id.pricing or 'dynamic'
			bom_obj = self.env['mrp.bom']
			bom = bom_obj.search([('product_id','=',self.product_id.id)], limit=1)
			if not bom:
				product_tmpl_id = self.product_id.product_tmpl_id
				bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
			if bom:
				components = bom.get_components(0,1,self.product_id.name)
				if new_vals['pricing'] == 'fixed':
					for comp in components:
						comp[2]['hide_prices'] = True
				new_vals['direct_child_ids'] = components
		else: # new product is not a kit
			new_vals['is_kit_order_line'] = False
			new_vals['pricing'] = 'fixed'
		self.update(new_vals)
	
	@api.depends('direct_child_ids')
	def _compute_unit_compo_price(self):
		for line in self:
			if line.is_kit_order_line:
				uc_price = 0
				for comp in line.direct_child_ids:
					uc_price += comp.shown_price
				line.unit_compo_price = uc_price
				line._refresh_price_unit()
	
	@api.onchange('unit_compo_price','product_uom_qty','pricing')
	def _refresh_price_unit(self):
		for line in self:
			if line.is_kit_order_line:
				if line.pricing == 'dynamic':
					line.price_unit = line.unit_compo_price
				else:
					line.price_unit = line.product_id.lst_price

	@api.multi
	def _init_components(self):
		"""
		Create records in 'sale.order.line.comp' for each component of a kit that have not yet been loaded.
		"""
		for line in self:
			if line.is_kit_order_line:
				comp_obj = line.env['sale.order.line.comp'].search([('order_line_id','=',self.id)])
				if line.pricing == 'dynamic':
					hide_prices = False
				else:
					hide_prices = True 
				for comp in comp_obj:
					comp.load_under_components(True,hide_prices)

	@api.model
	def create(self, vals):
		line = super(OFKitSaleOrderLine,self).create(vals)
		if line.is_kit_order_line:
			line._init_components()
			#line._refresh_price_unit()
		return line
	
	@api.multi
	def write(self,vals):
		super(OFKitSaleOrderLine,self).write(vals)
		if 'product_id' in vals:
			self._init_components()
		if 'pricing' in vals: # it is not possible to do it on the fly for some reason
			if vals['pricing'] == 'dynamic':
				self.direct_child_ids.toggle_hide_prices(False,True)
			if vals['pricing'] == 'fixed':
				self.direct_child_ids.toggle_hide_prices(True,True)
		return True
	
class OFKitSaleOrderLineComponent(models.Model):
	_name = 'sale.order.line.comp'
	_description = 'Sales Order Line Components'
	_order = 'bom_path'
	
	order_line_id = fields.Many2one('sale.order.line',string='Order Line',ondelete='cascade',required=True,readonly=True)
	order_id = fields.Many2one('sale.order', string='Order', related='order_line_id.order_id', readonly=True)
	bom_path = fields.Char(string='Kit Arch',help="Contains the chain of parents of this component")
	
	name = fields.Char(string='Name',required=True)
	
	product_id = fields.Many2one('product.product',string='Product',required=True)
	is_kit_order_comp = fields.Boolean(string="Is a kit",required=True, default=False,
							help="True if this comp is a kit itself. Also called an under-kit in that case")
	rec_lvl = fields.Integer(string="Recursion Level", help="1 for components of a kit. 2 for components of a kit inside a kit... etc.")
	parent_id = fields.Many2one('sale.order.line.comp',string='Parent Comp', ondelete='cascade')
	child_ids = fields.One2many('sale.order.line.comp', 'parent_id', string='Children Comps')
	load_children = fields.Boolean(string="Load children",
						help="odoo is currently unable to load components of components at once on the fly. \n \
						check this box to load this component under-components on the fly. \n \
						if you don't, all components will be loaded when you click 'save' on the order.")
	children_loaded = fields.Boolean(string="Children loaded")
	
	pricing = fields.Selection([
		('fixed','Fixed'),
		('dynamic','Dynamic')
		],string="Pricing", required=True, default='fixed',
			help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'dynamic', the price will be computed according to the components of the kit.")
	currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
	product_uom = fields.Many2one('product.uom', string='UoM', required=True)
	unit_price = fields.Monetary('Unit Price',digits=dp.get_precision('Product Price'),required=True,default=0.0)
	children_price = fields.Monetary('Unit Price',digits=dp.get_precision('Product Price'),compute='_compute_children_price')
	unit_cost = fields.Monetary('Unit Cost',digits=dp.get_precision('Product Price'))
	
	qty_bom_line = fields.Float(string='Qty / parent', digits=dp.get_precision('Product Unit of Measure'),
						help="Quantity per direct parent unit.")
	qty_so_line = fields.Float(string='Qty / kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
							help="Quantity per SO line kit unit")
	nb_units = fields.Float(string='Number of kits', related='order_line_id.product_uom_qty')
	qty_total = fields.Float(string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), 
								   compute='_compute_qty_total', help='total quantity equal to quantity per kit times number of kits')
	
	shown_price_total = fields.Monetary(string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_shown_price', 
							help="Equal to total quantity * unit price")
	shown_price = fields.Monetary(string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_shown_price', 
							help="Equal to quantity per so line unit * unit price")

	hide_prices = fields.Boolean(string="Hide prices")
	
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
	def onchange_product_id_comp(self):
		if self.is_kit_order_comp:
			# l'ancien produit était un kit, il faut supprimer ses composants
			self.child_ids = [(5,)]
			
		new_vals = {
			'name': self.product_id.name,
			'pricing': self.product_id.pricing or 'fixed',
			'product_uom': self.product_id.product_tmpl_id.uom_id,
			'unit_price': self.product_id.lst_price,
			'unit_cost': self.product_id.standard_price,
			'qty_bom_line': 1,
			}
		if self.parent_id:
			if not self.bom_path:
				bom_path = self.parent_id.bom_path + " -> " + self.parent_id.name
			else:
				bom_path = self.bom_path
			hide_prices = self.parent_id.hide_prices
			rec_lvl = self.parent_id.rec_lvl +1
			qty_so_line_parent = self.parent_id.qty_so_line
		else:
			if not self.bom_path: # on creation, when choosing a product
				bom_path = self.order_line_id.name
			else:
				bom_path = self.bom_path
			if self.order_line_id:
				if self.order_line_id.pricing == 'fixed':
					hide_prices = True
				else:
					hide_prices = False
			else:
				hide_prices = False
			rec_lvl = 1
			qty_so_line_parent = 1
		new_vals['qty_so_line'] = qty_so_line_parent
		new_vals['bom_path'] = bom_path
		new_vals['rec_lvl'] = rec_lvl
		new_vals['hide_prices'] = hide_prices
		
		if self.product_id.is_kit:
			# le nouveau produit est un kit, il faut ajouter ses composants
			new_vals['is_kit_order_comp'] = True
			new_vals['pricing'] = 'dynamic'
			bom_obj = self.env['mrp.bom']
			bom = bom_obj.search([('product_id','=',self.product_id.id)], limit=1)
			if not bom:
				product_tmpl_id = self.product_id.product_tmpl_id
				bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
			if bom:
				under_components = bom.get_components(rec_lvl,qty_so_line_parent,bom_path + " -> " + self.product_id.name)
				if hide_prices:
					for under_comp in under_components:
						under_comp[2]['hide_prices'] = True
				new_vals['child_ids'] = under_components
				new_vals['children_loaded'] = True
		else:
			# le nouveau produit n'est pas un kit
			new_vals['is_kit_order_comp'] = False
			new_vals['pricing'] = 'fixed'
		
		self.update(new_vals)
	
	@api.onchange('load_children')
	def onchange_load_children(self):
		"""
		checkbox to load components on the fly before saving.
		"""
		if self.load_children:
			self.load_under_components(False,self.hide_prices)
	
	@api.multi
	def load_under_components(self,recursive=False,hide_prices=False):
		#TODO: optimiser le cas recursif par appel à get_components_rec?
		for comp in self:
			if comp.is_kit_order_comp and not comp.children_loaded:
				bom_obj = self.env['mrp.bom']
				bom = bom_obj.search([('product_id','=',comp.product_id.id)], limit=1)
				if not bom:
					product_tmpl_id = comp.product_id.product_tmpl_id
					bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
				if bom:
					components = bom.get_components(comp.rec_lvl,comp.qty_so_line,comp.bom_path + " -> " + comp.product_id.name)
					if hide_prices:
						for under_comp in components:
							under_comp[2]['hide_prices'] = True
					comp.child_ids = components
				comp.children_loaded = True
				if recursive:
					comp.child_ids.load_under_components(True,hide_prices)
			else:
				comp.hide_prices = hide_prices

	@api.depends('child_ids')
	def _compute_children_price(self):
		for comp in self:
			if comp.is_kit_order_comp:
				if comp.children_loaded:
					comp.children_price = comp.get_prices_rec(False)
				else:
					bom_obj = self.env['mrp.bom']
					bom = bom_obj.search([('product_id','=',comp.product_id.id)], limit=1)
					if not bom:
						product_tmpl_id = comp.product_id.product_tmpl_id
						bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
					if bom:
						comp.children_price = bom.get_components_price(comp.qty_so_line,True)
						

	@api.multi
	def get_prices_rec(self,per_so_line=True,without_pricing=True):
		"""
		returns the price of the components in self and their children per unit SO or bom line
		doesn't take under-kits pricing into account if without_pricing
		"""
		res = 0
		for comp in self:
			if not comp.is_kit_order_comp: # comp is not a kit, stop condition
				if per_so_line:
					res += comp.qty_so_line * comp.unit_price
				else:
					res += comp.qty_bom_line * comp.unit_price
			elif without_pricing:
				res += comp.child_ids.get_prices_rec(per_so_line,without_pricing)
			elif comp.pricing == 'fixed': # comp is a kit with fixed pricing, stop condition
				if per_so_line:
					res += comp.qty_so_line * comp.unit_price
				else:
					res += comp.qty_bom_line * comp.unit_price
			else: # comp is a kit with dynamic pricing, recursive call
				res += comp.child_ids.get_prices_rec(per_so_line,without_pricing)
		return res

	@api.multi
	@api.depends('qty_so_line','unit_price','nb_units')
	def _compute_shown_price(self):
		for comp in self:
			if not comp.is_kit_order_comp:
				so_unit_price = comp.get_prices_rec()
			else:
				if comp.children_loaded:
					so_unit_price = comp.get_prices_rec()
				else:
					bom_obj = self.env['mrp.bom']
					bom = bom_obj.search([('product_id','=',comp.product_id.id)], limit=1)
					if not bom:
						product_tmpl_id = comp.product_id.product_tmpl_id
						bom = bom_obj.search([('product_tmpl_id','=',product_tmpl_id.id)], limit=1)
					if bom:
						so_unit_price = bom.get_components_price(comp.qty_so_line,True)
			comp.shown_price = so_unit_price
			comp.shown_price_total = so_unit_price * comp.nb_units
				
	
	@api.depends('qty_so_line','nb_units')
	def _compute_qty_total(self):
		for comp in self:
			comp.qty_total = comp.qty_so_line * comp.nb_units 
		
	@api.model
	def create(self, vals):
		if vals.get('parent_id') and not vals.get('order_line_id'):
			vals['order_line_id'] = self.browse(vals['parent_id']).order_line_id.id
		comp = super(OFKitSaleOrderLineComponent,self).create(vals)
		if not comp.bom_path:
			comp.bom_path = comp.order_line_id.name
		return comp
	
	@api.multi
	def write(self,vals):
		super(OFKitSaleOrderLineComponent,self).write(vals)
		return True
	
	