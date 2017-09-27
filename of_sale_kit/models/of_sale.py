# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp

class OFKitSaleOrder(models.Model):
	_inherit = 'sale.order'

	contains_kit = fields.Boolean(string='Contains a kit', compute='_compute_contains_kit')

	component_ids = fields.One2many('sale.order.line.comp', 'order_id', string='Components', domain=[('is_kit', '=', False)], readonly=True,
					help="Contains all kit components in this sale order that are not kits themselves.", oldname="components")

	@api.multi
	@api.depends('order_line.product_id')
	def _compute_contains_kit(self):
		line_obj = self.env['sale.order.line']
		for order in self:
			order.contains_kit = line_obj.search([("order_id", "=",order.id), ('is_kit', '=', True)], count=True) > 0

	kit_display_mode = fields.Selection([
        ('none', 'None'),
        ('collapse', 'Collapse'),
        #('collapse_expand','One line per kit, with detail'),
        ('expand', 'Expand'),
        ], string='Kit display mode', default='none',
            help="defines the way kits should be printed out in pdf reports:\n\
            - None: One line per kit. Nothing printed out about components\n\
            - Collapse: One line per kit, with minimal info about components\n\
            - Expand: One line per kit, plus one line per component")

	@api.multi
	def _prepare_invoice(self):
		"""
		Prepare the dict of values to create the new invoice for a sales order.
		Override of parent function
		"""
		invoice_vals = super(OFKitSaleOrder, self)._prepare_invoice()
		invoice_vals['kit_display_mode'] = self.kit_display_mode
		return invoice_vals

class OFKitSaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	child_ids = fields.One2many('sale.order.line.comp', 'order_line_id', string='Direct children', domain=[('parent_id', '=', False)],
							help="Contains all components that are direct children of this kit. An indirect child would be a component of a kit inside this kit for example.", oldname="direct_child_ids")
	is_kit = fields.Boolean(string='Is a kit', oldname="is_kit_order_line")

	price_compo = fields.Monetary('Compo Price/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_compo',
							help="Sum of the prices of all components necessary for 1 unit of this kit", oldname="unit_compo_price")
	cost_compo = fields.Monetary('Compo Cost/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_compo',
                                  help="Sum of the costs of all components necessary for 1 unit of this kit")

	pricing = fields.Selection([
		('fixed', 'Fixed'),
		('computed', 'Computed')
		], string="Pricing", required=True, default='fixed',
			help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'computed', the price will be computed according to the components of the kit.")

	def get_kit_descr_collapse(self):
		"""
		returns a string to be added to a kit name in PDF reports when kit display mode is set to 'Collapse'
		that string contains all components in this line that are not kits, plus their total quantities
		"""
		self.ensure_one()
		if not self.is_kit:
			return ""
		comp_obj = self.env['sale.order.line.comp']
		components = comp_obj.search([('order_line_id', '=', self.id), ('is_kit', '=', False)]) # get all comps that are not kits
		ir_model_data = self.env['ir.model.data']
		units_id = ir_model_data.get_object_reference('product', 'product_uom_unit')[1]
		res = []
		for comp in components:
			qty_int_val = int(comp.qty_total)
			if comp.product_uom.id == units_id: # uom is units, no need to print it
				qty = str(qty_int_val) # qty is an int because it's in units
				comp_str = (comp.default_code or comp.name) + ": " + qty
			else:
				if qty_int_val == comp.qty_total:
					qty = str(qty_int_val)
				else:
					qty = str(comp.qty_total)
				comp_str = (comp.default_code or comp.name) + ": " + qty + " " + comp.product_uom.name
			res.append(comp_str)
		res = " (" + ", ".join(res) + ")"
		return res

	def get_all_comps(self, only_leaves=False):
		"""
		Function used when printing out PDF reports in Expand mode, and when creating procurements on confirmation of the order.
		returns all components in this order line, in correct order (children components directly under their parent)
		"""
		def get_comp_comps(comp):
			if not comp.is_kit:
				return [comp] # stop condition
			if only_leaves: # meaning we don't want under-kits
				res = []
			else:
				res = [comp]
			for c in comp.child_ids:
				res += get_comp_comps(c) # recursive call
			return res
		self.ensure_one()
		if not self.is_kit:
			return []
		result = []
		for comp in self.child_ids:
			result += get_comp_comps(comp)
		return result

	@api.onchange('product_uom_qty', 'product_uom')
	def product_uom_change(self):
		self.ensure_one()
		super(OFKitSaleOrderLine, self).product_uom_change()
		self._refresh_price_unit()

	@api.multi
	@api.onchange('product_id')
	def product_id_change(self):
		res = super(OFKitSaleOrderLine, self).product_id_change()
		new_vals = {}
		if self.is_kit: # former product was a kit, we need to delete its components
			self.child_ids = [(5,)]
		if self.product_id.is_kit: # new product is a kit, we need to add its components
			new_vals['is_kit'] = True
			new_vals['pricing'] = self.product_id.pricing or 'computed'
			bom_obj = self.env['mrp.bom']
			bom = bom_obj.search([('product_id', '=', self.product_id.id)], limit=1)
			if not bom:
				product_tmpl_id = self.product_id.product_tmpl_id
				bom = bom_obj.search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)
			if bom:
				comp_ref = self.product_id.default_code or self.product_id.name_get()[0][1] or self.product_id.name
				components = bom.get_components(0, 1, comp_ref, 'sale')
				if new_vals['pricing'] == 'fixed':
					for comp in components:
						comp[2]['hide_prices'] = True
				new_vals['child_ids'] = components
		else: # new product is not a kit
			new_vals['is_kit'] = False
			new_vals['pricing'] = 'fixed'
		self.update(new_vals)
		
		return res

	@api.depends('child_ids')
	def _compute_price_compo(self):
		for line in self:
			if line.is_kit:
				uc_price = 0
				uc_cost = 0
				for comp in line.child_ids:
					uc_price += comp.price_per_line
					uc_cost += comp.cost_per_line
				line.price_compo = uc_price
				line.cost_compo = uc_cost
				line._refresh_price_unit()

	@api.onchange('price_compo', 'cost_compo', 'product_uom_qty', 'pricing', 'product_id')
	def _refresh_price_unit(self):
		for line in self:
			if line.is_kit:
				price = line.price_unit
				if line.pricing == 'computed':
					line.price_unit = line.price_compo
					if line.price_unit != price:
						line._compute_amount()
				#else:
				#	line.price_unit = line.product_id.lst_price
				line.purchase_price = line.cost_compo

	@api.multi
	def _init_components(self):
		"""
		Create records in 'sale.order.line.comp' for each component of a kit that have not yet been loaded.
		"""
		for line in self:
			if line.is_kit:
				comp_obj = line.env['sale.order.line.comp'].search([('order_line_id', '=', self.id), ('children_loaded', '=', False)])
				if line.pricing == 'computed':
					hide_prices = False
				else:
					hide_prices = True 
				for comp in comp_obj:
					comp.load_under_components(True, hide_prices)

	@api.onchange('is_kit')
	def _onchange_is_kit(self):
		if self.is_kit:
			if not self.product_id.is_kit: # a product that is not a kit is being made into a kit
				# we create a component with current product (for procurements, kits are ignored)
				comp_name = self.product_id.name_get()[0][1] or self.product_id.name
				new_comp_vals = {
					'product_id': self.product_id.id,
					'rec_lvl': 1,
					'name': comp_name,
					'default_code': self.product_id.default_code,
					'parent_chain': self.product_id.default_code or comp_name,
					'is_kit': False,
					'qty_per_line': 1,
					'product_uom': self.product_uom,
					'price_unit': self.product_id.list_price,
                    'cost_unit': self.product_id.standard_price,
                    'customer_lead': self.product_id.sale_delay,
					}

				self.update({
					'child_ids': [(0, 0, new_comp_vals)],
					'pricing': 'computed',
					'price_unit': self.price_compo,
					})
			else: # can happen if uncheck then recheck a kit
				new_vals = {}
				new_vals['pricing'] = self.product_id.pricing or 'computed'
				bom_obj = self.env['mrp.bom']
				bom = bom_obj.search([('product_id', '=', self.product_id.id)], limit=1)
				if not bom:
					product_tmpl_id = self.product_id.product_tmpl_id
					bom = bom_obj.search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)
				if bom:
					comp_ref = self.product_id.default_code or self.product_id.name_get()[0][1] or self.product_id.name
					components = bom.get_components(0, 1, comp_ref, 'sale')
					if new_vals['pricing'] == 'fixed':
						for comp in components:
							comp[2]['hide_prices'] = True
					new_vals['child_ids'] = components
				self.update(new_vals)
		else: # a product that was a kit is not anymore, we unlink its components
			self.update({
				'child_ids': [(5,)],
				'pricing': 'fixed',
				'price_unit': self.product_id.list_price,
				})

	@api.multi
	def _action_procurement_create(self):
		"""
		Creates a procurement order for lines in self. Call ._action_procurement_create() on components.
		"""
		lines = self.filtered(lambda line:not line.is_kit) # get all lines in self that are not kits
		res_order_lines = super(OFKitSaleOrderLine, lines)._action_procurement_create() # create POs for those lines

		kits = self - lines # get all lines that are kits
		components = self.env['sale.order.line.comp'].search([('order_line_id', 'in', kits._ids),('is_kit', '=', False)]) # get all comps that are not kits
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
		res = super(OFKitSaleOrderLine, self)._prepare_invoice_line(qty)
		if self.is_kit:
			res['is_kit'] = True
			res['pricing'] = self.pricing
		else:
			res['pricing'] = 'fixed'
			res['is_kit'] = False
		return res

	@api.multi
	def invoice_line_create(self, invoice_id, qty):
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
			if line.is_kit:
				kit_lines |= line
			else:
				other_lines |= line

		super(OFKitSaleOrderLine, other_lines).invoice_line_create(invoice_id, qty)
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
		if not self.is_kit:
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
		components = self.env['sale.order.line.comp'].search([('order_line_id', '=', self.id), ('is_kit', '=', False)]) # get all comps that are not kits
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		for comp in components:
			if comp.qty_delivered < comp.qty_total and not float_is_zero( comp.qty_delivered - comp.qty_total, precision_digits=precision ):
				return False
		return True

	@api.multi
	def update_underkit_delivered(self):
		"""
		updates underkits delivered quantities. At the moment we use all or nothing policy
		"""
		comp_obj = self.env['sale.order.line.comp']
		for line in self:
			if line.is_kit and line.qty_delivered != 0: # all or nothing policy
				# set all underkits of this line delivered quantity to their total quantity
				underkits = comp_obj.search([('order_line_id', '=', line.id), ('is_kit', '=', True)])
				for underkit in underkits:
					underkit.qty_delivered = underkit.qty_total

	@api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'cost_compo')
	def _product_margin(self):
		# Override of function from sale_margin
		for line in self:
			currency = line.order_id.pricelist_id.currency_id
			if line.is_kit:
				cost = line.cost_compo or line.product_id.cost_compo
			else:
				cost = line.purchase_price or line.product_id.standard_price
			line.margin = currency.round(line.price_subtotal - (cost * line.product_uom_qty))

	def _compute_margin(self, order_id, product_id, product_uom_id):
		# Override of function from sale_margin
		frm_cur = self.env.user.company_id.currency_id
		to_cur = order_id.pricelist_id.currency_id
		if product_id.is_kit:
			purchase_price = product_id.cost_compo
		else:
			purchase_price = product_id.standard_price
		if product_uom_id != product_id.uom_id:
			purchase_price = product_id.uom_id._compute_price(purchase_price, product_uom_id)
		ctx = self.env.context.copy()
		ctx['date'] = order_id.date_order
		price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
		return price

	@api.model
	def create(self, vals):
		line = super(OFKitSaleOrderLine, self).create(vals)
		if line.is_kit:
			line._init_components()
			if line.pricing == 'computed':
				line.price_unit = line.price_compo
			#line._refresh_price_unit()
		return line

	@api.multi
	def write(self, vals):
		if len(self._ids) == 1 and self.pricing == 'computed' and not self.price_unit == self.price_compo:
			vals['price_unit'] = self.price_compo
		super(OFKitSaleOrderLine, self).write(vals)
		if 'product_id' in vals or vals.get('is_kit') or 'child_ids' in vals:
			self._init_components()
		if 'pricing' in vals: # it is not possible to do it on the fly for some reason
			if vals['pricing'] == 'computed':
				self.child_ids.toggle_hide_prices(False, True)
			if vals['pricing'] == 'fixed':
				self.child_ids.toggle_hide_prices(True, True)
		return True

class OFKitSaleOrderLineComponent(models.Model):
	_name = 'sale.order.line.comp'
	_description = 'Sales Order Line Components'
	_order = 'parent_chain'

	order_line_id = fields.Many2one('sale.order.line', string='Order Line', ondelete='cascade', required=True, readonly=True)
	order_id = fields.Many2one('sale.order', string='Order', related='order_line_id.order_id', readonly=True)
	parent_chain = fields.Char(string='Parent chain', oldname="bom_path", help="""
Contains the chain of parents of this component
example: Kit A -> Kit B
means that the product is a component of Kit B which is itself a component of Kit A
""")

	name = fields.Char(string='Name', required=True)
	default_code = fields.Char(string='Prod ref')

	product_id = fields.Many2one('product.product', string='Product', required=True)
	is_kit = fields.Boolean(string="Is a kit", required=True, default=False, oldname="is_kit_order_comp",
							help="True if this comp is a kit itself. Also called an under-kit in that case")
	rec_lvl = fields.Integer(string="Recursion Level", help="1 for components of a kit. 2 for components of a kit inside a kit... etc.")
	parent_id = fields.Many2one('sale.order.line.comp', string='Parent Comp', ondelete='cascade')
	child_ids = fields.One2many('sale.order.line.comp', 'parent_id', string='Children Comps')
	load_children = fields.Boolean(string="Load direct children",
						help="odoo is currently unable to load components of components at once on the fly. \n \
						check this box to load this component under-components on the fly. \n \
						if you don't, all components will be loaded when you click 'save' on the order.")
	children_loaded = fields.Boolean(string="Children loaded") # no readonly for this or bug double children loading

	pricing = fields.Selection([
		('fixed', 'Fixed'),
		('computed', 'Computed')
		], string="Pricing", required=True, default='fixed',
			help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'computed', the price will be computed according to the components of the kit.")
	currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
	product_uom = fields.Many2one('product.uom', string='UoM', required=True)
	price_unit = fields.Monetary('Unit Price', digits=dp.get_precision('Product Price'), required=True,default=0.0, oldname="unit_price")
	price_children = fields.Monetary('Unit Price', digits=dp.get_precision('Product Price'), compute='_compute_prices',
						help="Unit price. In case of a kit, price of components necessary for one unit", oldname="children_price")
	cost_unit = fields.Monetary('Unit Cost', digits=dp.get_precision('Product Price'), oldname="unit_cost")
	cost_children = fields.Monetary('Unit Cost', digits=dp.get_precision('Product Price'), compute='_compute_prices',
						help="Unit cost. In case of a kit, cost of components necessary for one unit")
	cost_total = fields.Monetary(string='Subtotal Cost', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Cost of this component total quantity. Equal to total quantity * unit cost.")
	cost_per_line = fields.Monetary(string='Cost/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Cost of this component quantity necessary to make one unit of its order line kit. Equal to quantity per kit unit * unit cost.")

	qty_per_parent = fields.Float(string='Qty / parent', digits=dp.get_precision('Product Unit of Measure'), oldname='qty_bom_line', compute="_compute_qty_per_parent",
						help="Quantity per direct parent unit. Indicative value. Can differ from the quantity per line in case of a component of an under-kit.\n\
						example: 2 kit K1 -> 3 kit K2 -> 2 prod P. \nP.qty_per_parent = 2, \nP.qty_per_line = 6\nP.qty_total = 12",)
	qty_per_line = fields.Float(string='Qty / Kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0, oldname="qty_so_line",
							help="Quantity per kit unit (order line).\n\
						example: 2 kit K1 -> 3 kit K2 -> 2 prod P. \nP.qty_per_parent = 2, \nP.qty_per_line = 6\nP.qty_total = 12")

	nb_units = fields.Float(string='Number of kits', related='order_line_id.product_uom_qty', readonly=True)
	qty_total = fields.Float(string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty_total', 
								   help='total quantity equal to quantity per kit times number of kits.\n\
						example: 2 kit K1 -> 3 kit K2 -> 2 prod P. \nP.qty_per_parent = 2, \nP.qty_per_line = 6\nP.qty_total = 12')
	display_qty_changed = fields.Boolean(string="display qty changed message", default=False)
	price_total = fields.Monetary(string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Price of this component total quantity. Equal to total quantity * unit price.", oldname="price_per_line_total")
	price_per_line = fields.Monetary(string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Price of this component quantity necessary to make one unit of its order line kit. Equal to quantity per kit unit * unit price.", oldname="shown_price")

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

	qty_delivered = fields.Float(string='Delivered Qty', copy=False, digits=dp.get_precision('Product Unit of Measure'), default=0.0)

	@api.multi
	def toggle_hide_prices(self, hide, rec=True):
		for comp in self:
			if hide:
				comp.hide_prices =  True
			else:
				comp.hide_prices = False
			if comp.child_ids and rec:
				comp.child_ids.toggle_hide_prices(hide)

	@api.onchange('product_id')
	def _onchange_product_id(self):
		if self.is_kit:
			# l'ancien produit était un kit, il faut supprimer ses composants
			self.update({
				'child_ids': [(5,)],
				'children_loaded': False,
			})

		new_vals = {
			'name': self.product_id.name,
			'default_code': self.product_id.default_code,
			'pricing': self.product_id.pricing or 'fixed',
			'product_uom': self.product_id.product_tmpl_id.uom_id,
			'price_unit': self.product_id.lst_price,
			'cost_unit': self.product_id.standard_price,
			'customer_lead': self.product_id.sale_delay,
		}
		if self.parent_id:
			if not self.parent_chain:
				parent_chain = self.parent_id.parent_chain + " -> " + (self.parent_id.default_code or self.parent_id.name)
			else:
				parent_chain = self.parent_chain
			qty_per_line = self.parent_id.qty_per_line # 1 * parent qty_per_line
			hide_prices = self.parent_id.hide_prices
			rec_lvl = self.parent_id.rec_lvl +1
		else:
			if not self.parent_chain: # on creation, when choosing a product
				parent_chain = self.order_line_id.product_id.default_code or self.order_line_id.name
			else:
				parent_chain = self.parent_chain
			if self.order_line_id:
				if self.order_line_id.pricing == 'fixed':
					hide_prices = True
				else:
					hide_prices = False
			else:
				hide_prices = False
			qty_per_line = 1
			rec_lvl = 1
		if self.product_id:
			comp_name = self.product_id.name_get()[0][1] or self.product_id.name
			new_vals['name'] = comp_name
		new_vals['parent_chain'] = parent_chain
		new_vals['rec_lvl'] = rec_lvl
		new_vals['hide_prices'] = hide_prices
		new_vals['qty_per_line'] = qty_per_line

		if self.product_id.is_kit:
			# le nouveau produit est un kit, il faut ajouter ses composants
			new_vals['is_kit'] = True
			new_vals['pricing'] = 'computed'
			bom_obj = self.env['mrp.bom']
			bom = bom_obj.search([('product_id', '=', self.product_id.id)], limit=1)
			if not bom:
				product_tmpl_id = self.product_id.product_tmpl_id
				bom = bom_obj.search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)
			if bom:
				comp_ref = self.product_id.default_code or self.product_id.name_get()[0][1] or self.product_id.name
				under_components = bom.get_components(rec_lvl, qty_per_line, parent_chain + " -> " + comp_ref, 'sale')
				if hide_prices:
					for under_comp in under_components:
						under_comp[2]['hide_prices'] = True
				new_vals['child_ids'] = under_components
				new_vals['children_loaded'] = True
		else:
			# le nouveau produit n'est pas un kit
			new_vals['is_kit'] = False
			new_vals['pricing'] = 'fixed'

		self.update(new_vals)

	@api.onchange('qty_per_line')
	def _onchange_qty_per_line(self):
		if self.is_kit:
			self.display_qty_changed = True

	@api.onchange('load_children')
	def _onchange_load_children(self):
		"""
		checkbox to load components on the fly before saving.
		"""
		if self.load_children:
			self.load_under_components(False, self.hide_prices)

	@api.multi
	def load_under_components(self, recursive=False, hide_prices=False):
		"""
        Creates new components according to Bills of Materials.
        :param recursive: True if we want to load components of components as well. can't be True on the fly because odoo can't handle it atm.
        """
		#TODO: optimiser le cas recursif par appel à get_components_rec?
		for comp in self:
			if comp.is_kit and not comp.children_loaded:
				bom_obj = self.env['mrp.bom']
				bom = bom_obj.search([('product_id', '=', comp.product_id.id)], limit=1)
				if not bom:
					product_tmpl_id = comp.product_id.product_tmpl_id
					bom = bom_obj.search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)
				if bom:
					comp_ref = comp.product_id.default_code or comp.product_id.name_get()[0][1] or comp.product_id.name
					components = bom.get_components(comp.rec_lvl, comp.qty_per_line, comp.parent_chain + " -> " + comp_ref, 'sale')
					if hide_prices:
						for under_comp in components:
							under_comp[2]['hide_prices'] = True
					comp.child_ids = components
				comp.children_loaded = True
				if recursive:
					comp.child_ids.load_under_components(True, hide_prices)
			else:
				comp.hide_prices = hide_prices

	@api.depends('child_ids', 'qty_per_line', 'nb_units', 'children_loaded', 'product_id')
	def _compute_prices(self):
		for comp in self:
			qty_per_line = comp.qty_per_line
			if comp.is_kit:
				price_n_cost = comp.child_ids.get_prices_rec(1)
				price_children = price_n_cost['price']
				cost_children = price_n_cost['cost']
				if not comp.children_loaded and comp.product_id.current_bom_id: # a kit not loaded and not created on the fly
					price_n_cost_bom = comp.product_id.current_bom_id.get_components_price(1, True)
					price_children += price_n_cost_bom['price']
					cost_children += price_n_cost_bom['cost']
				# prices
				comp.price_children = price_children # unit price
				comp.price_per_line = price_children * qty_per_line
				comp.price_total = price_children * qty_per_line * comp.nb_units
				# costs
				comp.cost_children = cost_children # unit price
				comp.cost_per_line = cost_children * qty_per_line
				comp.cost_total = cost_children * qty_per_line * comp.nb_units
			else:
				# prices
				comp.price_children = comp.price_unit # no children but this way we can display unit prices on same column
				comp.price_per_line = comp.price_unit * qty_per_line
				comp.price_total = comp.price_unit * qty_per_line * comp.nb_units
				# costs
				comp.cost_children = comp.cost_unit # no children but this way we can display unit prices on same column
				comp.cost_per_line = comp.cost_unit * qty_per_line
				comp.cost_total = comp.cost_unit * qty_per_line * comp.nb_units

	@api.multi
	def get_prices_rec(self, qty_parent=1):
		"""
		returns the price and cost of the components in self and their children.
		doesn't take under-kits pricing into account.
		:param qty_parent: equal to 1 on first call of the function
		"""
		res = {'price': 0.0, 'cost': 0.0}
		for comp in self:
			if not comp.is_kit: # comp is not a kit, stop condition
				res['price'] += comp.price_unit * comp.qty_per_parent * qty_parent # can't use qty_per_line because the first caller of this function may not be the root component
				res['cost'] += comp.cost_unit * comp.qty_per_parent * qty_parent
			else:
				# case may happen where children are not loaded and still has children added on the fly, so we always add children price.
				price_n_cost = comp.child_ids.get_prices_rec(qty_parent * comp.qty_per_parent) # recursive call
				res['price'] += price_n_cost['price']
				res['cost'] += price_n_cost['cost']
				if not comp.children_loaded: # get prices from bom if children are not loaded
					bom_obj = self.env['mrp.bom']
					bom = bom_obj.search([('product_id', '=', comp.product_id.id)], limit=1)
					if not bom:
						product_tmpl_id = comp.product_id.product_tmpl_id
						bom = bom_obj.search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)
					if bom:
						price_n_cost = bom.get_components_price(comp.qty_per_line, True)
						res['price'] += price_n_cost['price']
						res['cost'] += price_n_cost['cost']
		return res

	@api.depends('qty_per_line', 'parent_id')
	def _compute_qty_per_parent(self):
		for comp in self:
			qty = comp.qty_per_line
			if comp.parent_id:
				qty /= comp.parent_id.qty_per_line
			comp.qty_per_parent = qty

	@api.depends('qty_per_line', 'nb_units')
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
		qty = 0.0
		for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
			if move.location_dest_id.usage == "customer":
				if not move.origin_returned_move_id:
					qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom)
			elif move.location_dest_id.usage == "internal" and move.to_refund_so:
				qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom)
		return qty

	@api.multi
	def _prepare_invoice_line_comp(self, inv_line_id):
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
			'default_code': self.default_code,
			'price_unit': self.price_unit,
			'uom_id': self.product_uom.id,
			'product_id': self.product_id.id or False,
			'order_comp_id': self.id,
			'parent_chain': self.parent_chain,
			'is_kit': self.is_kit,
			'rec_lvl': self.rec_lvl,
			'pricing': self.pricing,
			'currency_id': self.currency_id,
            'cost_unit': self.cost_unit,
            'qty_per_line': self.qty_per_line,
            'hide_prices': self.hide_prices,
            'invoice_line_id': inv_line_id
		}
		if self.is_kit:
			under_comps = []
			for comp in self.child_ids:
				under_comps += comp._prepare_invoice_line_comp(inv_line_id)
			new_comp['child_ids'] = under_comps
			new_comp['children_loaded'] = True
		res.append((0, 0, new_comp))
		return res

	@api.model
	def create(self, vals):
		if vals.get('parent_id') and not vals.get('order_line_id'): # for kits created on the fly
			vals['order_line_id'] = self.browse(vals['parent_id']).order_line_id.id
		comp = super(OFKitSaleOrderLineComponent, self).create(vals)
		if not comp.parent_chain:
			# use default_code in parent chain when present
			comp.parent_chain = comp.order_line_id.product_id.default_code or comp.order_line_id.name
		return comp

	@api.multi
	def write(self,vals):
		super(OFKitSaleOrderLineComponent, self).write(vals)
		for comp in self:
			if comp.display_qty_changed:
				# set to True in _onchange_qty_per_line, we need to set it back to False so the message doesn't stay
				comp.display_qty_changed = False
		return True

	