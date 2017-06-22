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
		], string='Kit display mode', default='expand',
			help="defines the way kits should be printed out in pdf reports:\n\
			- Collapse: One line per kit, with minimal info\n\
			- Expand: One line per kit, plus one line per component")

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
	
	def get_all_comps(self,only_leaves=False):
		"""
		Function used when printing out PDF reports in Expand mode, and when creating procurements on confirmation of the order.
		returns all components in this order line, in correct order (children components directly under their parent)
		"""
		def get_comp_comps(comp):
			if not comp.is_kit_order_comp:
				return [comp] # stop condition
			if only_leaves: # meaning we don't want under-kits
				res = []
			else:
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
				comp_name = self.product_id.name_get()[0][1] or self.product_id.name
				components = bom.get_components(0,1,comp_name,'sale')
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
					uc_price += comp.price_per_line
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
				comp_obj = line.env['sale.order.line.comp'].search([('order_line_id','=',self.id),('children_loaded','=',False)])
				if line.pricing == 'dynamic':
					hide_prices = False
				else:
					hide_prices = True 
				for comp in comp_obj:
					comp.load_under_components(True,hide_prices)

	@api.onchange('is_kit_order_line')
	def onchange_is_kit_order_line(self):
		if self.is_kit_order_line:
			if not self.product_id.is_kit: # a product that is not a kit is being made into a kit
				# we create a component with current product (for procurements, kits are ignored)
				comp_name = self.product_id.name_get()[0][1] or self.product_id.name
				new_comp_vals = {
					'product_id': self.product_id.id,
					'rec_lvl': 1,
					'name': comp_name,
					'bom_path': comp_name,
					'is_kit_order_comp': False,
					'qty_per_parent': 1,
					#'qty_per_line': 1,
					'product_uom': self.product_uom,
					'price_unit': self.product_id.list_price,
                    'unit_cost': self.product_id.standard_price,
                    'customer_lead': self.product_id.sale_delay,
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
	def _action_procurement_create(self):
		"""
		
		"""
		lines = self.filtered(lambda line:not line.is_kit_order_line) # get all lines in self that are not kits
		res_order_lines = super(OFKitSaleOrderLine, lines)._action_procurement_create() # create POs for those lines

		kits = self - lines # get all lines that are kits
		components = self.env['sale.order.line.comp'].search([('order_line_id','in',kits._ids),('is_kit_order_comp','=',False)]) # get all comps that are not kits
		res_order_comps = components._action_procurement_create()
		return res_order_lines + res_order_comps
	
	@api.multi
	def _prepare_invoice_line(self, qty):
		"""
		Prepare the dict of values to create the new invoice line for a sales order line.
		override to add 'is_kit' and 'pricing' fields. Components will be loaded after creation of the line.
		
		:param qty: float quantity to invoice
		"""
		self.ensure_one()
		res = super(OFKitSaleOrderLine,self)._prepare_invoice_line(qty)
		if self.is_kit_order_line:
			res['is_kit_invoice_line'] = True
			res['pricing'] = self.pricing
		else:
			res['pricing'] = 'fixed'
			res['is_kit_invoice_line'] = False
		
		return res
	
	@api.multi
	def invoice_line_create(self, invoice_id, qty):
		#TODO: to do
		"""
		Create an invoice line. The quantity to invoice can be positive (invoice) or negative
		(refund).
		split sale order lines between regular lines and kit lines
		
		:param invoice_id: integer
		:param qty: float quantity to invoice
		"""
		kit_lines = self.env['sale.order.line']
		other_lines = self.env['sale.order.line']
		for line in self:
			if line.is_kit_order_line:
				kit_lines |= line
			else:
				other_lines |= line
		
		super(OFKitSaleOrderLine,other_lines).invoice_line_create(invoice_id,qty)
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		ai_line_obj = self.env['account.invoice.line']
		for line in kit_lines:
			if not float_is_zero(qty, precision_digits=precision):
				vals = line._prepare_invoice_line(qty=qty)
				vals.update({
					'invoice_id': invoice_id, 
					'sale_line_ids': [(6, 0, [line.id])],
					'from_so_line': True,
					})
				new_line = ai_line_obj.create(vals)
				# now new_line has an id
				new_line.init_comps_from_so_line(line.id)
		
	@api.multi
	def _get_delivered_qty_hack(self):
		"""
		Computes the delivered quantity on sale order lines, based on done stock moves related to its procurements.
		At the moment we use an all or nothing policy for kits delivery.
		hack because of mrp_bom vs sale order lines that are kit made from BoMs
		"""
		self.ensure_one()
		if not self.is_kit_order_line:
			qty = super(OFKitSaleOrderLine, self)._get_delivered_qty()
			return qty
		if not self._all_comps_delivered():
			return 0.0
		else:
			return self.product_uom_qty
	
	@api.multi
	def _all_comps_delivered(self):
		"""
		check if all components were delivered entirely.
		"""
		self.ensure_one()
		components = self.env['sale.order.line.comp'].search([('order_line_id','=',self.id),('is_kit_order_comp','=',False)]) # get all comps that are not kits
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		for comp in components:
			if comp.qty_delivered < comp.qty_total and not float_is_zero( comp.qty_delivered - comp.qty_total, precision_digits=precision ):
				return False
		return True

	@api.model
	def create(self, vals):
		line = super(OFKitSaleOrderLine,self).create(vals)
		if line.is_kit_order_line:
			line._init_components()
			if line.pricing == 'dynamic':
				line.price_unit = line.unit_compo_price
			#line._refresh_price_unit()
		return line
	
	@api.multi
	def write(self,vals):
		if len(self._ids) == 1 and self.pricing == 'dynamic' and not self.price_unit == self.unit_compo_price:
			vals['price_unit'] = self.unit_compo_price
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
	rec_lvl = fields.Integer(string="Recursion Level", readonly=True, help="1 for components of a kit. 2 for components of a kit inside a kit... etc.")
	parent_id = fields.Many2one('sale.order.line.comp',string='Parent Comp', ondelete='cascade')
	child_ids = fields.One2many('sale.order.line.comp', 'parent_id', string='Children Comps')
	load_children = fields.Boolean(string="Load children",
						help="odoo is currently unable to load components of components at once on the fly. \n \
						check this box to load this component under-components on the fly. \n \
						if you don't, all components will be loaded when you click 'save' on the order.")
	children_loaded = fields.Boolean(string="Children loaded") # no readonly for this or bug double children loading
	
	pricing = fields.Selection([
		('fixed','Fixed'),
		('dynamic','Dynamic')
		],string="Pricing", required=True, default='fixed',
			help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'dynamic', the price will be computed according to the components of the kit.")
	currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
	product_uom = fields.Many2one('product.uom', string='UoM', required=True)
	price_unit = fields.Monetary('Unit Price',digits=dp.get_precision('Product Price'),required=True,default=0.0,oldname="unit_price")
	children_price = fields.Monetary('Unit Price',digits=dp.get_precision('Product Price'),compute='_compute_prices')
	unit_cost = fields.Monetary('Unit Cost',digits=dp.get_precision('Product Price'))
	
	qty_per_parent = fields.Float(string='Qty / parent', digits=dp.get_precision('Product Unit of Measure'),oldname='qty_bom_line',
						help="Quantity per direct parent unit.")
	qty_per_line = fields.Float(string='Qty / SOLine', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
							help="Quantity per SO line kit unit", compute="_compute_qty_per_line",oldname="qty_so_line")

	nb_units = fields.Float(string='Number of kits', related='order_line_id.product_uom_qty', readonly=True)
	qty_total = fields.Float(string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), 
								   compute='_compute_qty_total', help='total quantity equal to quantity per kit times number of kits')
	display_qty_changed = fields.Boolean(string="display qty changed message",default=False)
	price_total = fields.Monetary(string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Equal to total quantity * unit price", oldname="price_per_line_total")
	price_per_line = fields.Monetary(string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Equal to quantity per so line unit * unit price",oldname="shown_price")

	hide_prices = fields.Boolean(string="Hide prices", default=False)
	state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], related='order_id.state', string='Order Status', readonly=True, copy=False, store=True, default='draft')
	
	customer_lead = fields.Float(
        'Delivery Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer")
	procurement_ids = fields.One2many('procurement.order', 'sale_comp_id', string='Procurements')
	
	qty_delivered = fields.Float(string='Delivered', copy=False, digits=dp.get_precision('Product Unit of Measure'), default=0.0)

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
		if self.is_kit_order_comp:
			# l'ancien produit était un kit, il faut supprimer ses composants
			self.update({
				'child_ids': [(5,)],
				'children_loaded': False,
			})
			
		new_vals = {
			'name': self.product_id.name,
			'pricing': self.product_id.pricing or 'fixed',
			'product_uom': self.product_id.product_tmpl_id.uom_id,
			'price_unit': self.product_id.lst_price,
			'unit_cost': self.product_id.standard_price,
			'qty_per_parent': 1,
			'customer_lead': self.product_id.sale_delay,
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
			qty_per_line_parent = 1
		if self.product_id:
			comp_name = self.product_id.name_get()[0][1] or self.product_id.name
			new_vals['name'] = comp_name
		#new_vals['qty_per_line'] = qty_per_line_parent
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
				comp_name = self.product_id.name_get()[0][1] or self.product_id.name
				under_components = bom.get_components(rec_lvl,qty_per_line_parent,bom_path + " -> " + comp_name,'sale')
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
	
	@api.onchange('qty_per_parent')
	def _onchange_qty_per_parent(self):
		if self.is_kit_order_comp:
			self.display_qty_changed = True

	@api.onchange('load_children')
	def _onchange_load_children(self):
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
					comp_name = comp.product_id.name_get()[0][1] or comp.product_id.name
					components = bom.get_components(comp.rec_lvl,comp.qty_per_line,comp.bom_path + " -> " + comp_name,'sale')
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
			if comp.is_kit_order_comp:
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
			if not comp.is_kit_order_comp: # comp is not a kit, stop condition
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
	
	@api.multi
	def _prepare_order_comp_procurement(self, group_id=False):
		self.ensure_one()
		return {
			'name': self.name,
			'origin': self.order_id.name,
			'date_planned': datetime.strptime(self.order_id.date_order, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(days=self.customer_lead), # self.customer_lead
			'product_id': self.product_id.id,
			'product_qty': self.qty_total,
			'product_uom': self.product_uom.id,
			'company_id': self.order_id.company_id.id,
			'group_id': group_id,
			'location_id': self.order_id.partner_shipping_id.property_stock_customer.id,
            'route_ids': self.order_line_id.route_id and [(4, self.route_id.id)] or [],
            'warehouse_id': self.order_id.warehouse_id and self.order_id.warehouse_id.id or False,
            'partner_dest_id': self.order_id.partner_shipping_id.id,
            'sale_comp_id': self.id,
		}
	
	@api.multi
	def _action_procurement_create(self):
		"""
		Copy of sale.order.line._action_procurement_create()
		Create procurements based on quantity ordered. If the quantity is increased, new
		procurements are created. If the quantity is decreased, no automated action is taken.
		"""
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		new_procs = self.env['procurement.order']  # Empty recordset
		for comp in self:
			if comp.state != 'sale' or not comp.product_id._need_procurement():
				continue
			qty = 0.0
			for proc in comp.procurement_ids:
				qty += proc.product_qty
			if float_compare(qty, comp.qty_total, precision_digits=precision) >= 0:
				continue
			
			if not comp.order_id.procurement_group_id:
				vals = comp.order_id._prepare_procurement_group()
				comp.order_id.procurement_group_id = self.env["procurement.group"].create(vals)
			
			vals = comp._prepare_order_comp_procurement(group_id=comp.order_id.procurement_group_id.id)
			vals['product_qty'] = comp.qty_total - qty
			new_proc = self.env["procurement.order"].with_context(procurement_autorun_defer=True).create(vals)
			new_proc.message_post_with_view('mail.message_origin_link',
			    values={'self': new_proc, 'origin': comp.order_id},
			    subtype_id=self.env.ref('mail.mt_note').id)
			new_procs += new_proc
		new_procs.run()
		orders = list(set(x.order_id for x in self))
		for order in orders:
			reassign = order.picking_ids.filtered(lambda x: x.state=='confirmed' or ((x.state in ['partially_available', 'waiting']) and not x.printed))
			if reassign:
				reassign.do_unreserve()
				reassign.action_assign()
		return new_procs
	
	@api.multi
	def _get_delivered_qty(self):
		"""
		Computes the delivered quantity on sale order line components, based on done stock moves related to its procurements.
        """
		self.ensure_one()
		#super(OFKitSaleOrderLine, self)._get_delivered_qty()
		qty = 0.0
		for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
			if move.location_dest_id.usage == "customer":
				if not move.origin_returned_move_id:
					qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom)
			elif move.location_dest_id.usage == "internal" and move.to_refund_so:
				qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom)
		return qty
	
	@api.multi
	def _prepare_invoice_line_comp(self,inv_line_id):
		"""
		Prepare the dict of values to create a new invoice line comp, as well as all comps that are directly or indirectly its children
		
		:param inv_line_id: id of the invoice line where to put these comps
		"""
		self.ensure_one()
		res = []
		new_comp = {
			'name': self.name,
			#TODO: add sequence feature later
			#'sequence': self.sequence,
			'price_unit': self.price_unit,
			'quantity': self.qty_total,
			'uom_id': self.product_uom.id,
			'product_id': self.product_id.id or False,
			'order_comp_id': self.id,
			'bom_path': self.bom_path,
			'is_kit_invoice_comp': self.is_kit_order_comp,
			'rec_lvl': self.rec_lvl,
			'pricing': self.pricing,
			'currency_id': self.currency_id,
            'unit_cost': self.unit_cost,
            'qty_per_parent': self.qty_per_parent,
            'hide_prices': self.hide_prices,
            'invoice_line_id': inv_line_id
		}
		if self.is_kit_order_comp:
			under_comps = []
			for comp in self.child_ids:
				under_comps += comp._prepare_invoice_line_comp(inv_line_id)
			new_comp['child_ids'] = under_comps
			new_comp['children_loaded'] = True
		res.append((0,0,new_comp))
		return res

	@api.model
	def create(self, vals):
		if vals.get('parent_id') and not vals.get('order_line_id'): # for kits created on the fly
			vals['order_line_id'] = self.browse(vals['parent_id']).order_line_id.id
		comp = super(OFKitSaleOrderLineComponent,self).create(vals)
		if not comp.bom_path:
			comp.bom_path = comp.order_line_id.name
		return comp
	
	@api.multi
	def write(self,vals):
		super(OFKitSaleOrderLineComponent,self).write(vals)
		for comp in self:
			if comp.display_qty_changed:
				# set to True in onchange_qty_per_parent, we need to set it back to False so the message doesn't stay
				comp.display_qty_changed = False
		return True
	
	