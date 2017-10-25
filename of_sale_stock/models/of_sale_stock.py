# -*- coding: utf-8 -*-
# Part of Openfire. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp

class OFSaleStockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, required=True, related="company_id.currency_id")
    product_value = fields.Monetary('Value', digits=dp.get_precision('Product Price'), compute="_compute_product_value")

    @api.multi
    @api.depends('product_id.standard_price', 'product_qty')
    def _compute_product_value(self):
        for line in self:
            # @TODO: ajouter un paramètre config pour choisir la façon de calculer la valeur
            # @TODO: gérer le multi-currency
            line.product_value = line.product_id.standard_price * line.product_qty

    #@api.onchange('product_qty')

class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    stock_warning_setting = fields.Boolean(string="Avertissements de stock", required=True, default=False,
            help="Afficher les messages d'avertissement de stock?")

    @api.multi
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'stock_warning_setting', self.stock_warning_setting)
