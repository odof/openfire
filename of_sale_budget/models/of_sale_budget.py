# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError


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
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='order_id.currency_id', store=True, readonly=True)
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
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True, readonly=True)
    unit_cost = fields.Float(
        string=u"Coût unitaire", digits=dp.get_precision('Product Price'),
        required=True)
    total_cost = fields.Float(
        string=u"Coût", digits=dp.get_precision('Product Price'), required=True, compute='_compute_total_cost')
    product_uom_id = fields.Many2one(
        comodel_name='product.uom', string=u"Uom", related='product_id.uom_id', required=True, readonly=True)
    product_uom_qty = fields.Float(string=u"Qté", required=True, default=1.0)
    notes = fields.Char(string=u"Notes")

    @api.depends('unit_cost', 'product_uom_qty')
    def _compute_total_cost(self):
        for cost in self:
            cost.total_cost = cost.unit_cost * cost.product_uom_qty

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for cost in self:
            cost.unit_cost = cost.product_id.standard_price


class OFSaleOrderLaborCost(models.Model):
    _name = 'of.sale.order.labor.cost'
    _description = u"Tableau des frais de main d’oeuvre"

    hour_worksite_id = fields.Many2one(comodel_name='of.sale.order.hour.worksite', string=u"Désignation", required=True)
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande")
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True, readonly=True)
    type = fields.Selection(
        selection=[('computed', u"Calculé"), ('manual', u"Manuel")],
        string=u"Type", related='hour_worksite_id.type', required=True, readonly=True)
    total_cost = fields.Float(string=u"Coût", digits=dp.get_precision('Product Price'), compute='_compute_total_cost')
    hourly_cost = fields.Float(
        string=u"Coût horaire", digits=dp.get_precision('Product Price'))
    product_uom_qty = fields.Float(
        string=u"Qté", required=True, compute='_compute_product_uom_qty', inverse='_inverse_product_uom_qty')
    inverse_product_uom_qty = fields.Float(string=u"Qté", required=True, default=1.0)
    notes = fields.Char(string=u"Notes")

    @api.depends('hourly_cost', 'product_uom_qty')
    def _compute_total_cost(self):
        for cost in self:
            cost.total_cost = cost.hourly_cost * cost.product_uom_qty

    @api.depends('order_id.order_line.of_duration', 'inverse_product_uom_qty')
    def _compute_product_uom_qty(self):
        for cost in self:
            if cost.type == 'computed':
                cost.product_uom_qty = sum(cost.order_id.order_line.mapped('of_duration'))
            else:
                cost.product_uom_qty = cost.inverse_product_uom_qty

    def _inverse_product_uom_qty(self):
        for cost in self:
            if cost.type == 'manual':
                cost.inverse_product_uom_qty = cost.product_uom_qty

    @api.onchange('hour_worksite_id')
    def _onchange_hour_worksite_id(self):
        for cost in self:
            cost.hourly_cost = cost.hour_worksite_id.hourly_cost

    @api.constrains('type', 'order_id')
    def _check_description(self):
        if self.type == 'computed':
            if self.search_count([('order_id', '=', self.order_id.id), ('type', '=', 'computed')]) > 1:
                raise ValidationError(u"Il ne peut y avoir qu'une ligne de frais de "
                                      u"main d'oeuvre en type calculé par commande")


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
        """Met à jour l'onglet Budget"""
        budget_obj = self.env['of.sale.order.budget']
        budget_lines = self.of_budget_ids
        budget_lines_type = budget_lines.mapped('name')

        # On crée les lignes de budget si elles ne sont pas déjà créées
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

        # On met à jour les valeurs de chaque ligne
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
