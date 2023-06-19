# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
    order_id = fields.Many2one(
        comodel_name='sale.order', string=u"Commande", required=True, readonly=True, ondelete='cascade')
    currency_id = fields.Many2one(
        comodel_name='res.currency', related='order_id.currency_id', store=True, readonly=True)
    cost = fields.Float(string=u"Coût", digits=dp.get_precision('Product Price'), readonly=True)
    total_cost = fields.Float(
        string=u"Coût total", digits=dp.get_precision('Product Price'), compute='_compute_total_cost')
    sale_price = fields.Float(
        string=u"Prix de vente", digits=dp.get_precision('Product Price'), compute='_compute_sale_price')
    real_price = fields.Float(string=u"PV réel", digits=dp.get_precision('Product Price'), readonly=True)
    coeff = fields.Float(string=u"Coef. (%)", digits=dp.get_precision('Product Price'))
    margin_coeff = fields.Float(string=u"Coef. Marge", digits=dp.get_precision('Product Price'), default=1.0)
    real_coeff = fields.Float(
        string=u"Coef. réel", digits=dp.get_precision('Product Price'), compute='_compute_real_coeff')
    notes = fields.Char(string=u"Notes")

    @api.depends('cost', 'coeff')
    def _compute_total_cost(self):
        for budget in self:
            budget.total_cost = budget.cost * (1 + budget.coeff/100)

    @api.depends('total_cost', 'margin_coeff')
    def _compute_sale_price(self):
        for budget in self:
            budget.sale_price = budget.total_cost * budget.margin_coeff

    @api.depends('cost', 'real_price')
    def _compute_real_coeff(self):
        for budget in self:
            budget.real_coeff = budget.real_price / budget.cost if budget.cost else 1


class OFSaleOrderIndirectCost(models.Model):
    _name = 'of.sale.order.indirect.cost'
    _description = u"Tableau des frais indirects"

    product_id = fields.Many2one(comodel_name='product.product', string=u"Désignation", required=True)
    order_id = fields.Many2one(
        comodel_name='sale.order', string=u"Commande", required=True, readonly=True, ondelete='cascade')
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
            cost.unit_cost = cost.product_id.get_cost()


class OFSaleOrderLaborCost(models.Model):
    _name = 'of.sale.order.labor.cost'
    _description = u"Tableau des frais de main d’oeuvre"

    hour_worksite_id = fields.Many2one(comodel_name='of.sale.order.hour.worksite', string=u"Désignation", required=True)
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", ondelete='cascade')
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

    @api.depends('order_id.order_line.of_hour_worksite_id', 'order_id.order_line.of_duration_total',
                 'inverse_product_uom_qty')
    def _compute_product_uom_qty(self):
        for cost in self:
            if cost.type == 'computed':
                cost.product_uom_qty = sum(
                    cost.order_id.order_line.filtered(
                        lambda l: l.of_hour_worksite_id == cost.hour_worksite_id).mapped('of_duration_total'))
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

    @api.constrains('type', 'order_id', 'hour_worksite_id')
    def _check_description(self):
        if self.search_count(
                [('order_id', '=', self.order_id.id), ('hour_worksite_id', '=', self.hour_worksite_id.id)]) > 1:
            raise ValidationError(u"Il ne peut y avoir deux lignes avec la même désignation de main d'oeuvre")


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
        string=u"Tableau de budget", copy=True)
    of_indirect_cost_ids = fields.One2many(
        comodel_name='of.sale.order.indirect.cost', inverse_name='order_id',
        string=u"Frais indirects", copy=True)
    of_labor_cost_ids = fields.One2many(
        comodel_name='of.sale.order.labor.cost', inverse_name='order_id',
        string=u"Frais de main d’oeuvre", copy=True)

    @api.onchange('of_template_id')
    def onchange_template_id(self):
        res = super(SaleOrder, self).onchange_template_id()
        for line in self.order_line:
            if line.product_id:
                line.of_hour_worksite_id = \
                    line.product_id.of_hour_worksite_id.id \
                    or self.env.ref('of_sale_budget.of_sale_order_hour_worksite_data').id
        return res

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
                lambda sol: sol.of_product_type != 'service' or sol.of_subcontracted_service is False)
            purchase_budget_line.cost = sum(map(
                lambda x: x.product_uom_qty * x.purchase_price, purchase_order_lines))
            purchase_budget_line.real_price = sum(purchase_order_lines.mapped('price_subtotal'))

        outsourcing_budget_line = budget_lines.filtered(lambda line: line.name == 'outsourcing')
        if outsourcing_budget_line:
            outsourcing_order_lines = self.order_line.filtered(
                lambda sol: sol.of_product_type == 'service' and sol.of_subcontracted_service is True)
            outsourcing_budget_line.cost = sum(map(
                lambda x: x.product_uom_qty * x.purchase_price, outsourcing_order_lines))
            outsourcing_budget_line.real_price = sum(outsourcing_order_lines.mapped('price_subtotal'))

        indirect_cost_budget_line = budget_lines.filtered(lambda line: line.name == 'indirect_cost')
        if indirect_cost_budget_line:
            indirect_cost_budget_line.cost = sum(self.of_indirect_cost_ids.mapped('total_cost'))

        labor_cost_budget_line = budget_lines.filtered(lambda line: line.name == 'labor_cost')
        if labor_cost_budget_line:
            labor_cost_budget_line.cost = sum(self.of_labor_cost_ids.mapped('total_cost'))

        self.of_budget_ids = budget_lines
        self.update_sale_order_labor_cost()

    @api.multi
    def update_sale_order_labor_cost(self):
        labor_cost_obj = self.env['of.sale.order.labor.cost']

        for order in self:
            order_hour_worksite = order.order_line.mapped('of_hour_worksite_id')
            labor_cost_hour_worksite = order.of_labor_cost_ids.mapped('hour_worksite_id')
            hour_worksite_to_add = order_hour_worksite - labor_cost_hour_worksite

            # On récupère les lignes computed à supprimer
            hour_worksite_to_delete = labor_cost_hour_worksite.filtered(
                lambda l: l.type == 'computed') - order_hour_worksite

            for hour_worksite in hour_worksite_to_add:
                labor_cost_obj.create({
                    'order_id': order.id,
                    'hour_worksite_id': hour_worksite.id,
                    'product_uom_qty': sum(order.order_line.filtered(
                        lambda l: l.of_hour_worksite_id == hour_worksite).mapped('product_uom_qty')),
                })

            # On supprime les lignes computed en trop
            order.of_labor_cost_ids.filtered(lambda l: l.hour_worksite_id in hour_worksite_to_delete).unlink()

        self.mapped('of_labor_cost_ids')._onchange_hour_worksite_id()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_hour_worksite_id = fields.Many2one(
        comodel_name='of.sale.order.hour.worksite', string=u"Heures chantier")
    of_labor_cost = fields.Float(
        string=u"Coût main d'oeuvre", digits=dp.get_precision('Product Price'), compute='_compute_of_labor_cost')
    of_total_labor_cost = fields.Float(
        string=u"Total coût", digits=dp.get_precision('Product Price'), compute='_compute_of_labor_cost')

    @api.depends('of_hour_worksite_id', 'of_hour_worksite_id.hourly_cost',
                 'of_duration_total', 'purchase_price', 'product_uom_qty')
    def _compute_of_labor_cost(self):
        for line in self:
            line.of_labor_cost = line.of_hour_worksite_id.hourly_cost * line.of_duration_total
            line.of_total_labor_cost = line.of_labor_cost + (line.purchase_price * line.product_uom_qty)

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            self.of_hour_worksite_id = self.product_id.of_hour_worksite_id.id \
                                       or self.env.ref('of_sale_budget.of_sale_order_hour_worksite_data').id
        return res

    @api.multi
    def write(self, values):
        res = super(SaleOrderLine, self).write(values)

        if 'of_hour_worksite_id' in values:
            self.mapped('order_id').update_sale_order_labor_cost()

        return res


class OFSaleOrderLayoutCategory(models.Model):
    _inherit = 'of.sale.order.layout.category'

    labor_cost = fields.Float(
        string=u"Coût main d'oeuvre", digits=dp.get_precision('Product Price'), compute='_compute_labor_cost')
    total_labor_cost = fields.Float(
        string=u"Total coût", digits=dp.get_precision('Product Price'), compute='_compute_labor_cost')
    margin = fields.Float(string=u"Marge HT", compute='_compute_margin')
    pc_margin = fields.Float(string=u"% Marge", compute='_compute_margin')

    @api.depends('order_line_ids')
    def _compute_labor_cost(self):
        for layout_category in self:
            layout_category.labor_cost = sum(layout_category.order_line_ids.mapped('of_labor_cost'))
            layout_category.total_labor_cost = sum(layout_category.order_line_ids.mapped('of_total_labor_cost'))

    @api.depends('total_labor_cost', 'prix_vente')
    def _compute_margin(self):
        for layout_category in self:
            layout_category.margin = layout_category.prix_vente - layout_category.total_labor_cost
            layout_category.pc_margin = 100 * (1 - layout_category.total_labor_cost / layout_category.prix_vente) \
                if layout_category.prix_vente else - layout_category.total_labor_cost


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _default_of_hour_worksite_id(self):
        hour_worksite = self.env.ref('of_sale_budget.of_sale_order_hour_worksite_data', False)
        return hour_worksite and hour_worksite.id

    of_hour_worksite_id = fields.Many2one(
        comodel_name='of.sale.order.hour.worksite', string=u"Heures chantier", required=True,
        default=lambda self: self._default_of_hour_worksite_id())

    @api.model
    def create(self, values):
        res = super(ProductTemplate, self).create(values)
        if res.of_hour_worksite_id:
            res.of_hour_worksite_id.type = 'computed'
        return res

    @api.multi
    def write(self, values):
        res = super(ProductTemplate, self).write(values)
        for product in self:
            if product.of_hour_worksite_id:
                product.of_hour_worksite_id.type = 'computed'
        return res
