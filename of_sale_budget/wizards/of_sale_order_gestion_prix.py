# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    cost_prorata = fields.Selection(
        selection_add=[('total_cost', u"Coût total"), ('theorical_price', u"Prix théorique")])

    budget_init_margin = fields.Float(string=u"Marge initiale (budget)", compute='_compute_budget_margin')
    budget_init_margin_pc = fields.Float(string=u"% Marge initial (budget)", compute='_compute_budget_margin')
    budget_simu_margin = fields.Float(string=u"Marge simulée (budget)", compute='_compute_budget_margin')
    budget_simu_margin_pc = fields.Float(string=u"% Marge simulé (budget)", compute='_compute_budget_margin')

    @api.depends(
        'layout_category_ids', 'layout_category_ids.cost', 'layout_category_ids.labor_cost', 'montant_total_ht_initial',
        'montant_total_ht_simul')
    def _compute_budget_margin(self):
        for wizard in self:
            categs = wizard.layout_category_ids
            total_cost = sum(categs.mapped(lambda c: c.cost + c.labor_cost))
            init_sell_price = wizard.montant_total_ht_initial
            simu_sell_price = wizard.montant_total_ht_simul

            wizard.budget_init_margin = init_sell_price - total_cost
            wizard.budget_init_margin_pc = 100 * (1 - total_cost / init_sell_price) if init_sell_price else - total_cost
            wizard.budget_simu_margin = simu_sell_price - total_cost
            wizard.budget_simu_margin_pc = 100 * (1 - total_cost / simu_sell_price) if simu_sell_price else - total_cost


class GestionPrixLine(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix.line'

    duration = fields.Float(related='order_line_id.of_duration_total', string=u"Nombre d'heures", readonly=True)
    hour_worksite_id = fields.Many2one(
        related='order_line_id.of_hour_worksite_id', string=u"Type d'heures", readonly=True)

    def get_base_amount(self, order_line, cost_prorata, all_zero):
        """
        @param order_line: La ligne de commande sur laquelle on récupère les informations
        @param cost_prorata: Le type de prorata utilisé
        @param all_zero: Vrai si cost_prorata == 'cost' et tout les purchase price sont a 0,
                              si cost_prorata == 'price' et tout les price unit sont a 0,
                         Faux dans les autres cas
        """
        if cost_prorata == 'total_cost':
            return order_line.of_total_labor_cost / order_line.product_uom_qty \
                if order_line.product_uom_qty and order_line.of_total_labor_cost else 1.0
        elif cost_prorata == 'theorical_price':
            return order_line.of_theorical_price / order_line.product_uom_qty \
                if order_line.product_uom_qty and order_line.of_theorical_price else 1.0
        else:
            return super(GestionPrixLine, self).get_base_amount(order_line, cost_prorata, all_zero)

    def filter_lines(self, lines_select, cost_prorata):
        if cost_prorata == 'total_cost':
            lines_select = lines_select.filtered(lambda line: line.order_line_id.of_total_labor_cost) or lines_select
        elif cost_prorata == 'theorical_price':
            lines_select = lines_select.filtered(lambda line: line.order_line_id.of_theorical_price) or lines_select
        else:
            lines_select = super(GestionPrixLine, self).filter_lines(lines_select, cost_prorata)
        return lines_select


class GestionPrixLayoutCategory(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix.layout.category'

    duration = fields.Float(string=u"Nombre d'heures", compute='_compute_duration')
    cost_purchase = fields.Float(string=u"Coût achats", compute='_compute_price')
    cost_subcontracted_service = fields.Float(string=u"Coût sous-traitance", compute='_compute_price')
    labor_cost = fields.Float(string=u"Coût main d'oeuvre", compute='_compute_price')
    theorical_price = fields.Float(
        string=u"Prix de vente ht théorique", compute='_compute_price')
    theorical_coef = fields.Float(
        string=u"Coefficient total théorique", compute='_compute_price')

    budget_margin = fields.Float(string=u"Marge HT (budget)", compute='_compute_budget_margin')
    budget_margin_pc = fields.Float(string=u"% Marge (budget)", compute='_compute_budget_margin')

    @api.depends('line_ids')
    def _compute_duration(self):
        for categ in self:
            order_lines = categ.line_ids.mapped('order_line_id')
            categ.duration = sum(order_lines.mapped('of_duration_total'))

    @api.depends('line_ids')
    def _compute_price(self):
        super(GestionPrixLayoutCategory, self)._compute_price()
        for categ in self:
            order_lines = categ.line_ids.mapped('order_line_id')
            standard_lines = order_lines.filtered(lambda l: not l.of_subcontracted_service)
            subcontracted_service_lines = order_lines.filtered(lambda l: l.of_subcontracted_service)
            categ.cost_purchase = sum(standard_lines.mapped(lambda l: l.product_uom_qty * l.purchase_price))
            categ.cost_subcontracted_service = sum(
                subcontracted_service_lines.mapped(lambda l: l.product_uom_qty * l.purchase_price))
            categ.labor_cost = sum(order_lines.mapped('of_labor_cost'))
            theorical_price = sum(order_lines.mapped('of_theorical_price'))
            total_cost = sum(order_lines.mapped('of_total_labor_cost'))
            categ.theorical_price = theorical_price
            categ.theorical_coef = total_cost and theorical_price / total_cost or 1.0

    @api.depends('cost', 'labor_cost', 'simulated_price_subtotal')
    def _compute_budget_margin(self):
        for line in self:
            buy_price = line.cost + line.labor_cost
            sell_price = line.simulated_price_subtotal

            line.budget_margin = sell_price - buy_price
            line.budget_margin_pc = 100 * (1 - buy_price / sell_price) if sell_price else - buy_price
