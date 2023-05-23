# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model_cr_context
    def _auto_init(self):
        res = super(SaleConfigSettings, self)._auto_init()
        if not self.env['ir.values'].get_default('sale.config.settings', 'of_budget_purchase'):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_budget_purchase', 1.0)
        if not self.env['ir.values'].get_default('sale.config.settings', 'of_budget_outsourcing'):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_budget_outsourcing', 1.0)
        if not self.env['ir.values'].get_default('sale.config.settings', 'of_budget_indirect_cost'):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_budget_indirect_cost', 1.0)
        if not self.env['ir.values'].get_default('sale.config.settings', 'of_budget_labor_cost'):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_budget_labor_cost', 1.0)
        return res

    of_budget_purchase = fields.Float(
        string=u"(OF) Achats", digits=dp.get_precision('Product Price'),
        help=u"Coefficient de marge par défaut pour la ligne de budget 'Achats'")
    of_budget_outsourcing = fields.Float(
        string=u"(OF) Sous traitance", digits=dp.get_precision('Product Price'),
        help=u"Coefficient de marge par défaut pour la ligne de budget 'Sous traitance'")
    of_budget_indirect_cost = fields.Float(
        string=u"(OF) Frais indirects", digits=dp.get_precision('Product Price'),
        help=u"Coefficient de marge par défaut pour la ligne de budget 'Frais indirects'")
    of_budget_labor_cost = fields.Float(
        string=u"(OF) Frais de main d'oeuvre", digits=dp.get_precision('Product Price'),
        help=u"Coefficient de marge par défaut pour la ligne de budget 'Frais de main d'oeuvre'")

    @api.multi
    def set_of_budget_purchase_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_budget_purchase', self.of_budget_purchase)

    @api.multi
    def set_of_budget_outsourcing_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_budget_outsourcing', self.of_budget_outsourcing)

    @api.multi
    def set_of_budget_indirect_cost_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_budget_indirect_cost', self.of_budget_indirect_cost)

    @api.multi
    def set_of_budget_labor_cost_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_budget_labor_cost', self.of_budget_labor_cost)
