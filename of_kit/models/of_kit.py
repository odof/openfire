# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_is_kit = fields.Boolean(string="Is a kit")
    # store=True for domain searches and _sq_constraint
    is_kit_comp = fields.Boolean(
        string="Is a comp", compute='_compute_is_kit_comp', store=True, help="is a component of a kit")
    kit_line_ids = fields.One2many(
        comodel_name='of.product.kit.line', inverse_name='kit_id', string="Components", copy=True)

    price_comps = fields.Monetary(
        string="Compo Price/Kit", digits=dp.get_precision('Product Price'), compute='_compute_compo_price_n_cost',
        help="Sum of the prices of all components necessary for 1 unit of this kit")
    cost_comps = fields.Monetary(
        string="Compo Cost/Kit", digits=dp.get_precision('Product Price'), compute='_compute_compo_price_n_cost',
        help="Sum of the costs of all components necessary for 1 unit of this kit")
    seller_price_comps = fields.Monetary(
        string="Compo Purchase price/Kit", digits=dp.get_precision('Product Price'),
        compute='_compute_compo_price_n_cost',
        help="Sum of the purchase prices of all components necessary for 1 unit of this kit")

    of_price_used = fields.Monetary(
        string="Used Price", digits=dp.get_precision('Product Price'), compute='_compute_of_price_used',
        help="Price that will be taken into account in sale orders and invoices."
             "Either list price or the price of its components, dependant on the pricing.")

    of_pricing = fields.Selection(
        [
            ('fixed', 'Fixed'),
            ('computed', 'Computed'),
        ], string="Pricing", required=True, default='fixed',
        help="This field is only relevant if the product is a kit."
             "It represents the way the price should be computed.\n"
             "if set to 'fixed', the price of it's components won't be taken into account"
             "and the price will be the one of the kit.\n"
             "if set to 'computed', the price will be computed according to the components of the kit.")

    kit_count = fields.Integer(string="# Kits", compute='_compute_kit_count')
    comp_count = fields.Integer(string="# Comps", compute='_compute_comp_count')

    _sql_constraints = [
        ('kit_n_comp_constraint',
         'CHECK ( NOT(of_is_kit AND is_kit_comp) )',
         _("A product can not be a kit and a kit component at the same time !"))
    ]

    def get_invoice_kit_data(self):
        self.ensure_one()
        res = {'of_pricing': self.of_pricing}
        lines = [(5,)]
        comp_vals = {}
        if self.of_pricing == 'fixed':
            comp_vals['hide_prices'] = True
        for line in self.kit_line_ids:
            comp_vals = comp_vals.copy()
            comp_vals['product_id'] = line.product_id.id
            comp_vals['product_uom_id'] = line.product_uom_id.id
            comp_vals['qty_per_kit'] = line.product_qty
            comp_vals['sequence'] = line.sequence
            comp_vals['name'] = line.product_id.name_get()[0][1] or line.product_id.name
            comp_vals['price_unit'] = line.product_id.list_price
            comp_vals['cost_unit'] = line.product_id.get_cost()
            lines.append((0, 0, comp_vals))
        res['kit_line_ids'] = lines
        return res

    def get_saleorder_kit_data(self):
        self.ensure_one()
        res = {'of_pricing': self.of_pricing}
        lines = [(5,)]
        comp_vals = {}
        if self.of_pricing == 'fixed':
            comp_vals['hide_prices'] = True
        for line in self.kit_line_ids:
            comp_vals = comp_vals.copy()
            comp_vals['product_id'] = line.product_id.id
            comp_vals['product_uom_id'] = line.product_uom_id.id
            comp_vals['qty_per_kit'] = line.product_qty
            comp_vals['sequence'] = line.sequence
            comp_vals['name'] = line.product_id.name_get()[0][1] or line.product_id.name
            comp_vals['price_unit'] = line.product_id.of_price_used
            comp_vals['cost_unit'] = line.product_id.get_cost()
            comp_vals['customer_lead'] = line.product_id.sale_delay
            lines.append((0, 0, comp_vals))
        res['kit_line_ids'] = lines
        return res

    @api.multi
    @api.depends('kit_line_ids')
    def _compute_compo_price_n_cost(self):
        for product_tmpl in self:
            price = cost = purchase_price = 0.0
            if product_tmpl.of_is_kit:
                for line in product_tmpl.kit_line_ids:
                    price += line.product_id.uom_id._compute_price(line.product_id.list_price,
                                                                   line.product_uom_id) * line.product_qty
                    cost += line.product_id.uom_id._compute_price(line.product_id.get_cost(),
                                                                  line.product_uom_id) * line.product_qty
                    purchase_price += line.product_id.uom_id._compute_price(
                        line.product_id.of_seller_price, line.product_uom_id) * line.product_qty
            product_tmpl.price_comps = price
            product_tmpl.cost_comps = cost
            product_tmpl.seller_price_comps = purchase_price

    @api.multi
    @api.depends('kit_line_ids')
    def _compute_comp_count(self):
        for product_tmpl in self:
            product_tmpl.comp_count = len(product_tmpl.kit_line_ids)

    @api.multi
    @api.depends('price_comps', 'of_pricing')
    def _compute_of_price_used(self):
        for product_tmpl in self:
            if product_tmpl.of_is_kit:
                if product_tmpl.of_pricing == 'fixed':
                    product_tmpl.of_price_used = product_tmpl.list_price
                else:
                    product_tmpl.of_price_used = product_tmpl.price_comps
            else:
                product_tmpl.of_price_used = product_tmpl.list_price

    @api.multi
    @api.depends(
        'list_price', 'standard_price', 'of_theoretical_cost', 'price_comps', 'cost_comps', 'of_pricing', 'of_is_kit')
    def _compute_marge(self):
        for product_tmpl in self:
            if product_tmpl.of_is_kit:
                if product_tmpl.of_pricing == 'fixed':
                    price = product_tmpl.list_price
                else:
                    price = product_tmpl.price_comps
                if price:
                    product_tmpl.marge = (price - product_tmpl.cost_comps) * 100.00 / price
                else:
                    product_tmpl.marge = 0
            else:
                super(ProductTemplate, product_tmpl)._compute_marge()

    @api.onchange('of_is_kit')
    def _onchange_of_is_kit(self):
        self.ensure_one()
        if not self.of_is_kit:
            self.kit_line_ids = [(5,)]

    @api.depends('product_variant_ids', 'product_variant_ids.is_kit_comp')
    def _compute_is_kit_comp(self):
        for product_tmpl in self:
            product_tmpl.is_kit_comp = any(product.is_kit_comp for product in product_tmpl.product_variant_ids)

    @api.depends('product_variant_ids', 'product_variant_ids.kit_count')
    def _compute_kit_count(self):
        templates = self.env['product.template']
        for product_tmpl in self:
            kit_count = 0
            for variant in product_tmpl.product_variant_ids:
                kit_count += variant.kit_count
            product_tmpl.kit_count = kit_count
            # product_tmpl needs its is_kit_comp field updated
            if (not product_tmpl.is_kit_comp and kit_count > 0) or (product_tmpl.is_kit_comp and kit_count == 0):
                templates |= product_tmpl
        if len(templates) > 0:
            templates._compute_is_kit_comp()

    @api.multi
    def action_view_kits(self):
        action = self.env.ref('of_kit.of_template_open_kit').read()[0]
        action['domain'] = [('kit_line_ids.product_id.product_tmpl_id', 'in', [self.ids])]
        return action


class ProductProduct(models.Model):
    _inherit = 'product.product'

    kit_count = fields.Integer(string="# Kits", compute='_compute_kit_count')
    # store=True for domain searches and _sq_constraint
    is_kit_comp = fields.Boolean(
        string="Is a comp", compute='_compute_is_kit_comp', store=True, help="is a component of a kit")

    def _compute_kit_count(self):
        read_group_res = self.env['of.product.kit.line']\
            .read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        mapped_data = dict([(data['product_id'][0], data['product_id_count']) for data in read_group_res])
        for product in self:
            kit_count = mapped_data.get(product.id, 0)
            product.kit_count = kit_count

    def get_saleorder_kit_data(self):
        self.ensure_one()
        return self.product_tmpl_id.get_saleorder_kit_data()

    def get_invoice_kit_data(self):
        self.ensure_one()
        return self.product_tmpl_id.get_invoice_kit_data()

    def _compute_is_kit_comp(self):
        # this method will be called upon creation or change of a kit_line for its related product
        # (workaround store=True)
        read_group_res = self.env['of.product.kit.line']\
            .read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        mapped_data = dict([(data['product_id'][0], data['product_id_count']) for data in read_group_res])
        for product in self:
            product.is_kit_comp = mapped_data.get(product.id, 0) > 0


class OfProductKitLine(models.Model):
    _name = 'of.product.kit.line'
    _order = 'kit_id, sequence'

    kit_id = fields.Many2one(
        comodel_name='product.template', string="Kit", domain="[('is_kit_comp', '=', False)]",
        help="Kit containing this as component", ondelete='cascade')
    product_id = fields.Many2one(
        comodel_name='product.product', string="Product", domain="[('of_is_kit', '=', False)]", required=True,
        help="Product this line references")
    product_qty = fields.Float(
        string="Qty / Kit", digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0,
        help="Quantity per kit unit.")
    product_uom_categ_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    product_uom_id = fields.Many2one(
        comodel_name='product.uom', string="UoM", domain="[('category_id', '=', product_uom_categ_id)]", required=True)
    product_price = fields.Float(related='product_id.list_price', readonly=True)
    product_cost = fields.Float(compute='_compute_product_cost', digits=dp.get_precision('Product Price'))
    sequence = fields.Integer(string="Sequence", default=10)

    @api.multi
    @api.depends('product_id')
    def _compute_product_cost(self):
        for kit_line in self:
            kit_line.product_cost = kit_line.product_id.get_cost()

    @api.constrains('kit_id', 'product_id')
    @api.multi
    def _check_product_not_kit(self):
        for kit_line in self:
            if kit_line.kit_id.id == kit_line.product_id.product_tmpl_id.id:
                return False
        return True

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_uom_id = self.product_id.uom_id

    @api.model
    def create(self, vals):
        line = super(OfProductKitLine, self).create(vals)
        line.kit_id.type = 'service'
        line.product_id._compute_is_kit_comp()
        return line

    @api.multi
    def write(self, vals):
        if len(self) == 1 and 'product_id' in vals:
            products = self.env['product.product']
            products |= self.product_id
        super(OfProductKitLine, self).write(vals)
        if len(self) == 1 and 'product_id' in vals:
            products |= self.product_id
            products._compute_is_kit_comp()
        if len(self) == 1 and 'kit_id' in vals:
            self.kit_id.type = 'service'
        return True

    @api.multi
    def unlink(self):
        products = self.env['product.product']
        for kit_line in self:
            products |= kit_line.product_id
        super(OfProductKitLine, self).unlink()
        products._compute_is_kit_comp()


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    of_sale_comp_id = fields.Many2one(comodel_name='of.saleorder.kit.line', string="Sale Order Kit Component")

    def _get_sale_order(self):
        # fonction définie dans of_purchase
        self.ensure_one()
        sale_order = super(ProcurementOrder, self)._get_sale_order()
        if not sale_order:
            sale_comp = self.of_sale_comp_id
            if not sale_comp:
                move = self.move_dest_id
                sale_comp = move and move.procurement_id and move.procurement_id.of_sale_comp_id
            sale_order = sale_comp and sale_comp.order_id or False
        return sale_order


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.one
    @api.depends('move_lines.procurement_id.sale_line_id.order_id',
                 'move_lines.procurement_id.of_sale_comp_id.kit_id.order_line_id.order_id')
    def _compute_sale_id(self):
        for move in self.move_lines:
            if move.procurement_id.sale_line_id:
                self.sale_id = move.procurement_id.sale_line_id.order_id
                return
            elif move.procurement_id.of_sale_comp_id.kit_id.order_line_id:
                self.sale_id = move.procurement_id.of_sale_comp_id.kit_id.order_line_id.order_id
                return

    def _search_sale_id(self, operator, value):
        moves = self.env['stock.move'].search(
            [('picking_id', '!=', False),
             '|', ('procurement_id.sale_line_id.order_id', operator, value),
                  ('procurement_id.of_sale_comp_id.kit_id.order_line_id.order_id', operator, value)]
        )
        return [('id', 'in', moves.mapped('picking_id').ids)]


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_done(self):
        # Update delivered quantities on sale order lines that are not kits
        result = super(StockMove, self).action_done()
        # Update delivered quantities on sale order line components
        sale_order_components = self.filtered(lambda move: move.product_id.expense_policy == 'no')\
            .mapped('procurement_id.of_sale_comp_id')  # bug mal initialisé of_sale_comp_id?
        for comp in sale_order_components:
            comp.qty_delivered = comp._get_delivered_qty()
        lines = sale_order_components.mapped('kit_id.order_line_id')
        # Update delivered quantities on sale order lines that are kits
        for line in lines:
            qty_delivered = line._get_delivered_qty_hack()
            if qty_delivered != 0:
                line.qty_delivered = qty_delivered
        return result


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def _update_purchase_price(self):
        super(PurchaseOrder, self)._update_purchase_price()
        procurement_obj = self.env['procurement.order']
        for order in self:
            for line in order.order_line:
                procurements = procurement_obj.search([('purchase_line_id', '=', line.id)])
                moves = procurements.mapped('move_dest_id')
                kit_sale_lines = moves.mapped('procurement_id').mapped('of_sale_comp_id')
                kit_sale_lines.write({'cost_unit': line.price_unit * line.product_id.property_of_purchase_coeff})
                kit_sale_lines.mapped('kit_id').mapped('order_line_id').refresh_cost_comps()
