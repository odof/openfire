# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp


class OFSaleOrderBudget(models.Model):
    _name = 'of.sale.order.budget'
    _description = u"Tableau de budget"

    name = fields.Selection(
        selection=[
            ('purchase', u"Achats"),
            ('outsourcing', u"Sous traitance"),
            ('indirect_cost', u"Frais indirects"),
            ('labor_cost', u"Frais de main d'oeuvre"),
        ], string=u"Désignation", required=True, readonly=True)
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", required=True, readonly=True)
    cost = fields.Float(string=u"Coût", digits=dp.get_precision('Product Price'), readonly=True)
    total_cost = fields.Float(
        string=u"Coût total", digits=dp.get_precision('Product Price'), compute='_compute_total_cost')
    sale_price = fields.Float(
        string=u"Prix de vente", digits=dp.get_precision('Product Price'), compute='_compute_sale_price')
    coeff = fields.Float(string=u"Coef. (%)", digits=dp.get_precision('Product Price'))
    margin_coeff = fields.Float(string=u"Coef. Marge", digits=dp.get_precision('Product Price'), default=1.0)
    notes = fields.Char(string=u"Notes")

    @api.depends('cost', 'coeff')
    def _compute_total_cost(self):
        for budget in self:
            budget.total_cost = budget.cost * (1 + budget.coeff/100)

    @api.depends('total_cost', 'margin_coeff')
    def _compute_sale_price(self):
        for budget in self:
            budget.sale_price = budget.total_cost * budget.margin_coeff


class OFSaleOrderIndirectCost(models.Model):
    _name = 'of.sale.order.indirect.cost'
    _description = u"Tableau des frais indirects"

    product_id = fields.Many2one(comodel_name='product.product', string=u"Désignation", required=True)
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", required=True, readonly=True)
    unit_cost = fields.Float(
        string=u"Coût unitaire", digits=dp.get_precision('Product Price'),
        required=True, related='product_id.standard_price', store=True)
    total_cost = fields.Float(
        string=u"Coût", digits=dp.get_precision('Product Price'), required=True, compute='_compute_total_cost')
    product_uom_id = fields.Many2one(
        comodel_name='product.uom', string=u"Uom", required=True, related='product_id.uom_id')
    product_uom_qty = fields.Float(string=u"Qté", required=True, default=1.0)
    notes = fields.Char(string=u"Notes")

    @api.depends('unit_cost', 'product_uom_qty')
    def _compute_total_cost(self):
        for cost in self:
            cost.total_cost = cost.unit_cost * cost.product_uom_qty


class OFSaleOrderLaborCost(models.Model):
    _name = 'of.sale.order.labor.cost'
    _description = u"Tableau des frais de main d’oeuvre"

    hour_worksite_id = fields.Many2one(comodel_name='of.sale.order.hour.worksite', string=u"Désignation", required=True)
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande")
    type = fields.Selection(
        selection=[('computed', u"Calculé"), ('manual', u"Manuel")],
        string=u"Type", required=True, related='hour_worksite_id.type', store=True)
    total_cost = fields.Float(string=u"Coût", digits=dp.get_precision('Product Price'), compute='_compute_total_cost')
    hourly_cost = fields.Float(
        string=u"Coût horaire", digits=dp.get_precision('Product Price'),
        related='hour_worksite_id.hourly_cost', store=True)
    product_uom_qty = fields.Float(string=u"Qté", required=True, default=1.0)
    notes = fields.Char(string=u"Notes")

    @api.depends('hourly_cost', 'product_uom_qty')
    def _compute_total_cost(self):
        for cost in self:
            cost.total_cost = cost.hourly_cost * cost.product_uom_qty


class OFSaleOrderHourWorksite(models.Model):
    _name = 'of.sale.order.hour.worksite'
    _description = u"Heures chantier"
    _order = 'sequence'

    sequence = fields.Integer(string=u"Séquence", default=10)
    name = fields.Char(string=u"Désignation", required=True)
    type = fields.Selection(
        selection=[('computed', u"Calculé"), ('manual', u"Manuel")], string=u"Type", required=True, default='manual')
    hourly_cost = fields.Float(string=u"Coût horaire", digits=dp.get_precision('Product Price'))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_budget_ids = fields.One2many(
        comodel_name='of.sale.order.budget', inverse_name='order_id',
        string=u"Tableau de budget")
    of_indirect_cost_ids = fields.One2many(
        comodel_name='of.sale.order.indirect.cost', inverse_name='order_id',
        string=u"Frais indirects")
    of_labor_cost_ids = fields.One2many(
        comodel_name='of.sale.order.labor.cost', inverse_name='order_id',
        string=u"Frais de main d’oeuvre")

    def action_of_budget_ids(self):
        print('action_of_budget_ids : %s' % self)
        budget_obj = self.env['of.sale.order.budget']
        budget_lines = self.of_budget_ids
        budget_lines_type = budget_lines.mapped('name')
        if 'purchase' not in budget_lines_type:
            budget_line = budget_obj.create({'name': 'purchase', 'order_id': self.id})
            budget_lines += budget_line
        if 'outsourcing' not in budget_lines_type:
            budget_line = budget_obj.create({'name': 'outsourcing', 'order_id': self.id})
            budget_lines += budget_line
        if 'indirect_cost' not in budget_lines_type:
            budget_line = budget_obj.create({'name': 'indirect_cost', 'order_id': self.id})
            budget_lines += budget_line
        if 'labor_cost' not in budget_lines_type:
            budget_line = budget_obj.create({'name': 'labor_cost', 'order_id': self.id})
            budget_lines += budget_line
        print('budget_lines : %s' % budget_lines)

        purchase_budget_line = budget_lines.filtered(lambda line: line.name == 'purchase')
        if purchase_budget_line:
            purchase_order_lines = self.order_line.filtered(
                lambda sol: sol.product_id.property_subcontracted_service is False)
            purchase_budget_line.cost = sum(map(
                lambda x: x.product_uom_qty * x.purchase_price, purchase_order_lines))

        outsourcing_budget_line = budget_lines.filtered(lambda line: line.name == 'outsourcing')
        if outsourcing_budget_line:
            outsourcing_order_lines = self.order_line.filtered(
                lambda sol: sol.product_id.property_subcontracted_service is True)
            outsourcing_budget_line.cost = sum(map(
                lambda x: x.product_uom_qty * x.purchase_price, outsourcing_order_lines))

        indirect_cost_budget_line = budget_lines.filtered(lambda line: line.name == 'indirect_cost')
        if indirect_cost_budget_line:
            indirect_cost_budget_line.cost = sum(self.of_indirect_cost_ids.mapped('total_cost'))

        labor_cost_budget_line = budget_lines.filtered(lambda line: line.name == 'labor_cost')
        if labor_cost_budget_line:
            labor_cost_budget_line.cost = sum(self.of_labor_cost_ids.mapped('total_cost'))

        self.of_budget_ids = budget_lines
