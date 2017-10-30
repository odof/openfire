# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import odoo.addons.decimal_precision as dp

class OFKitSaleOrder(models.Model):
	_inherit = 'sale.order'

	comp_ids = fields.One2many('of.saleorder.kit.line', 'order_id', string='Components',
					help="Contains all kit components in this sale order.")
	of_contains_kit = fields.Boolean(string='Contains a kit', compute='_compute_of_contains_kit')

	"""
	implementation future -> ajouter les composants d'un kit en tant que lignes de commandes
	of_inser_nom = fields.Many2one('product.template', string="Insert Kit lines",
						help="select a kit to add its components as sale order lines.")"""

	@api.multi
	@api.depends('order_line.product_id')
	def _compute_of_contains_kit(self):
		comp_obj = self.env['of.saleorder.kit.line']
		for order in self:
			order.of_contains_kit = comp_obj.search([("order_id", "=", order.id)], count=True) > 0

	of_kit_display_mode = fields.Selection([
		('none', 'None'),
		('collapse', 'Collapse'),
		('expand', 'Expand'),
		], string='Kit display mode', default='expand',
			help="defines the way kits and their components should be printed out in pdf reports:\n\
			- None: One line per kit. Nothing printed out about components\n\
			- Collapse: One line per kit, with minimal info\n\
			- Expand: One line per kit, plus one line per component")

	"""
	implementation future -> ajouter les composants d'un kit en tant que lignes de commandes
	@api.onchange('of_inser_nom')
	def _onchange_of_inser_nom(self):
		self.ensure_one()
		if not self.of_inser_nom:
			return
		new_vals = self.of_inser_nom.get_saleorder_kit_nom_data()
		new_vals['of_inser_nom'] = False
		self.update(new_vals)"""

	@api.multi
	def _prepare_invoice(self):
		"""
		Prepare the dict of values to create the new invoice for a sales order.
		Override of parent function
		"""
		invoice_vals = super(OFKitSaleOrder, self)._prepare_invoice()
		invoice_vals['of_kit_display_mode'] = self.of_kit_display_mode
		return invoice_vals

class OFKitSaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	kit_id = fields.Many2one('of.saleorder.kit', string="Components")
	of_is_kit = fields.Boolean(string='Is a kit')

	price_comps = fields.Monetary('Compo Price/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
							help="Sum of the prices of all components necessary for 1 unit of this kit", oldname="unit_compo_price")
	cost_comps = fields.Monetary('Compo Cost/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
                                  help="Sum of the costs of all components necessary for 1 unit of this kit")
	of_pricing = fields.Selection([
        ('fixed', 'Fixed'),
        ('computed', 'Computed')
        ], string="Pricing", required=True, default='fixed',
            help="This field is only relevant if the product is a kit. It represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'computed', the price will be computed according to the components of the kit.")

	sale_kits_to_unlink = fields.Boolean(string="sale kits to unlink?", default=False, help="True if at least 1 sale kit needs to be deleted from database")

	def get_kit_descr_collapse(self):
		"""
		returns a string to be added to a kit name in PDF reports when kit display mode is set to 'Collapse'
		that string contains all components in this line that are not kits, plus their total quantities
		"""
		self.ensure_one()
		if not self.of_is_kit:
			return ""
		components = self.kit_id.kit_line_ids
		ir_model_data = self.env['ir.model.data']
		units_id = ir_model_data.get_object_reference('product', 'product_uom_unit')[1]
		res = []
		for comp in components:
			qty_int_val = int(comp.qty_total)
			if comp.product_uom_id.id == units_id: # uom is units, no need to print it
				qty = str(qty_int_val) # qty is an int because it's in units
				comp_str = (comp.default_code or comp.name) + ": " + qty
			else:
				if qty_int_val == comp.qty_total:
					qty = str(qty_int_val)
				else:
					qty = str(comp.qty_total)
				comp_str = (comp.default_code or comp.name) + ": " + qty + " " + comp.product_uom_id.name
			res.append(comp_str)
		res = " (" + ", ".join(res) + ")"
		return res

	@api.multi
	@api.depends('kit_id.kit_line_ids')
	def _compute_price_comps(self):
		for line in self:
			if line.kit_id:
				line.price_comps = line.kit_id.price_comps
				line.cost_comps = line.kit_id.cost_comps

	@api.onchange('price_comps', 'cost_comps', 'of_pricing', 'product_id')
	def _refresh_price_unit(self):
		for line in self:
			if line.of_is_kit:
				price = line.price_unit
				if line.of_pricing == 'computed':
					line.price_unit = line.price_comps
					if line.price_unit != price:
						line._compute_amount()
				line.purchase_price = line.cost_comps

	@api.multi
	@api.onchange('product_id')
	def product_id_change(self):
		res = super(OFKitSaleOrderLine, self).product_id_change()
		new_vals = {}
		if self.kit_id:  # former product was a kit -> unlink it's kit_id
			self.kit_id.write({"to_unlink": True})
			new_vals['kit_id'] = False
			new_vals["sale_kits_to_unlink"] = True
		if not self.product_id:
			return res
		if self.product_id.of_is_kit:  # new product is a kit, we need to add its components
			new_vals['of_is_kit'] = True
			new_vals['of_pricing'] = self.product_id.of_pricing
			sale_kit_vals = self.product_id.get_saleorder_kit_data()
			sale_kit_vals["qty_order_line"] = self.product_uom_qty
			new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)
		else:  # new product is not a kit
			new_vals['of_is_kit'] = False
			new_vals['of_pricing'] = 'fixed'
		self.update(new_vals)
		return res

	@api.onchange('product_uom_qty', 'product_uom')
	def product_uom_change(self):
		self.ensure_one()
		super(OFKitSaleOrderLine, self).product_uom_change()
		self._refresh_price_unit()

	@api.onchange('of_pricing')
	def _onchange_of_pricing(self):
		self.ensure_one()
		if self.of_pricing:
			if self.kit_id:
				self.kit_id.write({'of_pricing': self.of_pricing})
				self._refresh_price_unit()

	@api.onchange('of_is_kit')
	def _onchange_of_is_kit(self):
		new_vals = {}
		if self.kit_id:  # former product was a kit -> unlink it's kit_id
			self.kit_id.write({"to_unlink": True})
			new_vals["kit_id"] = False
			new_vals["sale_kits_to_unlink"] = True
		if self.of_is_kit:  # checkbox got checked
			if not self.product_id.of_is_kit: # a product that is not a kit is being made into a kit
				# we create a component with current product (for procurements, kits are ignored)
				new_comp_vals = {
					'product_id': self.product_id.id,
					'name': self.product_id.name_get()[0][1] or self.product_id.name,
					'default_code': self.product_id.default_code,
					'qty_per_kit': 1,
					'product_uom_id': self.product_uom.id or self.product_id.uom_id.id,
					'price_unit': self.product_id.list_price,
                    'cost_unit': self.product_id.standard_price,
                    'customer_lead': self.product_id.sale_delay,
                    'hide_prices': False,
					}
				sale_kit_vals = {
					'of_pricing': 'computed',
					'kit_line_ids': [(0, 0, new_comp_vals)],
					}
				new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)
				new_vals["of_pricing"] = "computed"
			else: # can happen if uncheck then recheck a kit
				new_vals['of_pricing'] = self.product_id.of_pricing
				sale_kit_vals = self.product_id.get_saleorder_kit_data()
				new_vals["kit_id"] = self.env["of.saleorder.kit"].create(sale_kit_vals)

		else: # a product that was a kit is not anymore, we unlink its components
			new_vals["of_pricing"] = 'fixed'
			new_vals["price_unit"] = self.product_id.list_price
		self.update(new_vals)
		self._refresh_price_unit()

	@api.onchange('kit_id')
	def _onchange_kit_id(self):
		self.ensure_one()
		if self.kit_id:
			self._compute_price_comps()
			self._refresh_price_unit()

	@api.multi
	def _action_procurement_create(self):
		"""
		Creates a procurement order for lines in self. Call ._action_procurement_create() on components.
		"""
		lines = self.filtered(lambda line:not line.of_is_kit) # get all lines in self that are not kits
		res_order_lines = super(OFKitSaleOrderLine, lines)._action_procurement_create() # create POs for those lines

		kits = self - lines # get all lines that are kits
		components = self.env['of.saleorder.kit.line'].search([('kit_id.order_line_id', 'in', kits._ids)]) # get all comps
		res_order_comps = components._action_procurement_create()
		return res_order_lines + res_order_comps

	@api.multi
	def _get_delivered_qty_hack(self):
		"""
		Computes the delivered quantity on sale order lines, based on done stock moves related to its procurements.
		At the moment we use an all or nothing policy for kits delivery.
		hack because of mrp_bom vs sale order lines that are kit made from BoMs
		"""
		self.ensure_one()
		if not self.of_is_kit:
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
		components = self.kit_id.kit_line_ids or []
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		for comp in components:
			if comp.qty_delivered < comp.qty_total and not float_is_zero( comp.qty_delivered - comp.qty_total, precision_digits=precision ):
				return False
		return True

	@api.multi
	def _prepare_invoice_line(self, qty):
		"""
		Prepare the dict of values to create the new invoice line for a sales order line.
		override to add 'of_is_kit' and 'of_pricing' fields. Components will be loaded after creation of the line.
		
		:param qty: float quantity to invoice
		"""
		self.ensure_one()
		res = super(OFKitSaleOrderLine, self)._prepare_invoice_line(qty)
		if self.of_is_kit:
			res['of_is_kit'] = True
			res['of_pricing'] = self.of_pricing
		else:
			res['of_pricing'] = 'fixed'
			res['of_is_kit'] = False
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
			if line.of_is_kit:
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
				new_line.init_kit_from_so_line(line.id)

	"""
	implementation future -> marges dans les devis
	@api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'cost_comps')
	def _product_margin(self):
		# Override of function from sale_margin
		for line in self:
			currency = line.order_id.pricelist_id.currency_id
			if line.of_is_kit:
				cost = line.cost_comps or line.product_id.cost_comps
			else:
				cost = line.purchase_price or line.product_id.standard_price
			line.margin = currency.round(line.price_subtotal - (cost * line.product_uom_qty))

	def _compute_margin(self, order_id, product_id, product_uom_id):
		# Override of function from sale_margin
		frm_cur = self.env.user.company_id.currency_id
		to_cur = order_id.pricelist_id.currency_id
		if product_id.of_is_kit:
			purchase_price = product_id.cost_comps
		else:
			purchase_price = product_id.standard_price
		if product_uom_id != product_id.uom_id:
			purchase_price = product_id.uom_id._compute_price(purchase_price, product_uom_id)
		ctx = self.env.context.copy()
		ctx['date'] = order_id.date_order
		price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
		return price"""

	@api.model
	def create(self,vals):
		if vals.get("sale_kits_to_unlink"):
			self.env["of.saleorder.kit"].search([("to_unlink", "=", True)]).unlink()
			vals.pop("sale_kits_to_unlink")
		line = super(OFKitSaleOrderLine, self).create(vals)
		sale_kit_vals = {'order_line_id': line.id, 'name': line.name, 'of_pricing': line.of_pricing}
		line.kit_id.write(sale_kit_vals)
		return line

	@api.multi
	def write(self,vals):
		if vals.get("sale_kits_to_unlink") or self.sale_kits_to_unlink:
			self.env["of.saleorder.kit"].search([("to_unlink", "=", True)]).unlink()
			vals["sale_kits_to_unlink"] = False
		update_ol_id = False
		if len(self) == 1 and vals.get("kit_id") and not self.kit_id:
			# a sale_order_kit was added
			update_ol_id = True
		elif len(self) == 1 and vals.get("name") and self.kit_id:
			# line changed name
			update_ol_id = True
		elif 'of_pricing' in vals:
			update_ol_id = True
		if len(self) == 1 and ((self.of_pricing == 'computed' and not vals.get('of_pricing')) or vals.get('of_pricing') == 'computed'):
			vals['price_unit'] = vals.get('price_comps', self.price_comps)  # price_unit is equal to price_comps if pricing is computed
		super(OFKitSaleOrderLine, self).write(vals)
		if update_ol_id:
			sale_kit_vals = {'order_line_id': self.id}
			if vals.get("name"):
				sale_kit_vals["name"] = vals.get("name")
			if vals.get("of_pricing"):
				sale_kit_vals["of_pricing"] = vals.get("of_pricing")
			self.kit_id.write(sale_kit_vals)
		return True

class OFSaleOrderKit(models.Model):
	_name = 'of.saleorder.kit'

	order_line_id = fields.Many2one("sale.order.line", string="Order line", ondelete="cascade")

	name = fields.Char(string='Name', required=True, default="draft saleorder kit")
	kit_line_ids = fields.One2many('of.saleorder.kit.line', 'kit_id', string="Components")

	qty_order_line = fields.Float(string="Order Line Qty", related="order_line_id.product_uom_qty", readonly=True)
	currency_id = fields.Many2one(related='order_line_id.currency_id', store=True, string='Currency', readonly=True)
	price_comps = fields.Monetary('Compo Price/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
							help="Sum of the prices of all components necessary for 1 unit of this kit", oldname="unit_compo_price")
	cost_comps = fields.Monetary('Compo Cost/Kit', digits=dp.get_precision('Product Price'), compute='_compute_price_comps',
                                  help="Sum of the costs of all components necessary for 1 unit of this kit")
	qty_invoiced = fields.Float(related="order_line_id.qty_invoiced", readonly=True)
	state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], related='order_line_id.state', string='Order Status', copy=False, store=True, default='draft')
	to_unlink = fields.Boolean(string="to unlink?", default=False)
	of_pricing = fields.Selection([
        ('fixed', 'Fixed'),
        ('computed', 'Computed')
        ], string="Pricing", required=True, default='computed',
            help="This field represents the way the price should be computed. \n \
                if set to 'fixed', the price of it's components won't be taken into account and the price will be the one of the kit. \n \
                if set to 'computed', the price will be computed according to the components of the kit.")

	@api.multi
	@api.depends('kit_line_ids')
	def _compute_price_comps(self):
		for kit in self:
			price = 0.0
			cost = 0.0
			if kit.kit_line_ids:
				for comp in kit.kit_line_ids:
					price += comp.price_unit * comp.qty_per_kit
					cost += comp.cost_unit * comp.qty_per_kit
				kit.price_comps = price
				kit.cost_comps = cost

	@api.multi
	def _prepare_account_kit(self, inv_line_id):
		"""
		Prepare the dict of values to create a new invoice line comp

		:param inv_line_id: id of the invoice line where to put these comps
		"""
		self.ensure_one()
		account_kit_vals = {
			'name': self.name,
			'of_pricing': self.of_pricing,
			'invoice_line_id': inv_line_id,
			'to_unlink': self.to_unlink,
			}
		lines = [(5,)]
		comp_vals = {}
		for line in self.kit_line_ids:
			comp_vals = line._prepare_account_kit_comp()
			lines.append((0, 0, comp_vals))
		account_kit_vals["kit_line_ids"] = lines
		return account_kit_vals

	@api.multi
	def account_kit_create(self, inv_line_id):
		account_kit_obj = self.env['of.invoice.kit']
		for kit in self:
			account_kit_vals = kit._prepare_account_kit(inv_line_id)
			account_kit_obj.create(account_kit_vals)

	@api.model
	def _clear_db(self):
		not_linked = self.search([('order_line_id', '=', False)])
		kits_to_link = self.env['sale.order.line'].search([('kit_id', 'in', not_linked._ids)])
		for kit in kits_to_link:
			kit.kit_id.order_line_id = kit.id
			not_linked -= kit.kit_id
		not_linked.unlink()

class OFSaleOrderKitLine(models.Model):
	_name = 'of.saleorder.kit.line'
	_order = "kit_id, sequence"

	kit_id = fields.Many2one('of.saleorder.kit', string="Kit", ondelete="cascade")
	order_id = fields.Many2one('sale.order', string="Order", related="kit_id.order_line_id.order_id")

	name = fields.Char(string='Name', required=True)
	default_code = fields.Char(string='Prod ref')
	sequence = fields.Integer(string=u'Sequence', default=10)

	product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('of_is_kit', '=', False)]")
	currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
	product_uom_id = fields.Many2one('product.uom', string='UoM', required=True)
	price_unit = fields.Monetary('Unit Price', digits=dp.get_precision('Product Price'), required=True,default=0.0, oldname="unit_price")
	cost_unit = fields.Monetary('Unit Cost', digits=dp.get_precision('Product Price'))
	cost_total = fields.Monetary(string='Subtotal Cost', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Cost of this component total quantity. Equal to total quantity * unit cost.")
	cost_per_kit = fields.Monetary(string='Cost/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Cost of this component quantity necessary to make one unit of its order line kit. Equal to quantity per kit unit * unit cost.")

	qty_per_kit = fields.Float(string='Qty / Kit', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0, oldname="qty_per_line",
							help="Quantity per kit unit (order line).\n\
						example: 2 kit K1 -> 3 prod P. \nP.qty_per_kit = 3\nP.qty_total = 6")

	nb_kits = fields.Float(string='Number of kits', related='kit_id.qty_order_line', readonly=True)
	qty_total = fields.Float(string='Total Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty_total', 
								   help='total quantity equal to quantity per kit times number of kits.')
	#display_qty_changed = fields.Boolean(string="display qty changed message", default=False)
	price_total = fields.Monetary(string='Subtotal Price', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Price of this component total quantity. Equal to total quantity * unit price.", oldname="price_per_line_total")
	price_per_kit = fields.Monetary(string='Price/Kit', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_prices', 
							help="Price of this component quantity necessary to make one unit of its order line kit. Equal to quantity per kit unit * unit price.")
	kit_pricing = fields.Selection(related="kit_id.of_pricing", readonly=True)
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
	procurement_ids = fields.One2many('procurement.order', 'of_sale_comp_id', string='Procurements')

	qty_delivered = fields.Float(string='Delivered Qty', copy=False, digits=dp.get_precision('Product Unit of Measure'), default=0.0)
	qty_delivered_updateable = fields.Boolean(compute='_compute_qty_delivered_updateable', string='Can Edit Delivered', readonly=True, default=True)
	invoiced = fields.Boolean("Invoiced", compute="_compute_invoiced")  # for readonly in XML

	@api.onchange('product_id')
	def _onchange_product_id(self):
		#@TODO: handle case product is a kit (domain, error or load components
		if self.product_id:
			new_vals = {
				'name': self.product_id.name_get()[0][1] or self.product_id.name,
				'default_code': self.product_id.default_code,
				'product_uom_id': self.product_id.product_tmpl_id.uom_id,
				'price_unit': self.product_id.list_price,
				'cost_unit': self.product_id.standard_price,
				'customer_lead': self.product_id.sale_delay,
			}
			if self.kit_id.order_line_id:
				if self.kit_id.order_line_id.of_pricing == 'fixed':
					hide_prices = True
				else:
					hide_prices = False
			else:
				hide_prices = self.hide_prices or False
			new_vals['hide_prices'] = hide_prices

			self.update(new_vals)

	@api.multi
	@api.depends('price_unit', 'cost_unit', 'qty_per_kit', 'nb_kits')
	def _compute_prices(self):
		for comp in self:
			qty_per_kit = comp.qty_per_kit
			# prices
			comp.price_per_kit = comp.price_unit * qty_per_kit
			comp.price_total = comp.price_unit * qty_per_kit * comp.nb_kits
			# costs
			comp.cost_per_kit = comp.cost_unit * qty_per_kit
			comp.cost_total = comp.cost_unit * qty_per_kit * comp.nb_kits

	@api.multi
	@api.depends('qty_per_kit', 'nb_kits')
	def _compute_qty_total(self):
		for comp in self:
			comp.qty_total = comp.qty_per_kit * comp.nb_kits 

	@api.multi
	@api.depends("kit_id")
	def _compute_invoiced(self):
		for kit_line in self:
			kit_line.invoiced = kit_line.kit_id.order_line_id and kit_line.kit_id.order_line_id.qty_invoiced

	@api.multi
	@api.depends('product_id.invoice_policy', 'order_id.state')
	def _compute_qty_delivered_updateable(self):
		for line in self:
			line.qty_delivered_updateable = (line.order_id.state == 'sale') and (line.product_id.track_service == 'manual') and (line.product_id.expense_policy == 'no')

	@api.multi
	def _prepare_order_comp_procurement(self, group_id=False):
		self.ensure_one()
		return {
			'name': self.name,
			'origin': self.order_id.name,
			'date_planned': datetime.strptime(self.order_id.date_order, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(days=self.customer_lead), # self.customer_lead
			'product_id': self.product_id.id,
			'product_qty': self.qty_total,
			'product_uom': self.product_uom_id.id,
			'company_id': self.order_id.company_id.id,
			'group_id': group_id,
			'location_id': self.order_id.partner_shipping_id.property_stock_customer.id,
            'route_ids': self.kit_id.order_line_id.route_id and [(4, self.route_id.id)] or [],
            'warehouse_id': self.order_id.warehouse_id and self.order_id.warehouse_id.id or False,
            'partner_dest_id': self.order_id.partner_shipping_id.id,
            'of_sale_comp_id': self.id,
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
					qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom_id)
			elif move.location_dest_id.usage == "internal" and move.to_refund_so:
				qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom_id)
		return qty

	@api.multi
	def _prepare_account_kit_comp(self):
		"""
		Prepare the dict of values to create a new account.kit.line

		:param kit_id: id of the invoice line where to put these comps
		"""
		self.ensure_one()
		new_comp_vals = {
			'name': self.name,
			'sequence': self.sequence,
			'default_code': self.default_code,
			'price_unit': self.price_unit,
			'product_uom_id': self.product_uom_id.id,
			'product_id': self.product_id.id or False,
			'order_comp_id': self.id,
            'cost_unit': self.cost_unit,
            'qty_per_kit': self.qty_per_kit,
            'hide_prices': self.hide_prices,
		}
		return new_comp_vals
