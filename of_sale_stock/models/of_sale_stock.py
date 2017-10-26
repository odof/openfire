# -*- coding: utf-8 -*-
# Part of Openfire. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp

class OFSaleStockInventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"

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

class OFSaleStockSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        # inhiber la vérification de stock
        afficher_warning = self.env['ir.values'].get_default('sale.config.settings', 'of_stock_warning_setting')
        if afficher_warning:
            return super(OFSaleStockSaleOrderLine, self)._onchange_product_id_check_availability()

class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_stock_warning_setting = fields.Boolean(string="Avertissements de stock", required=True, default=False,
            help="Afficher les messages d'avertissement de stock?")

    @api.multi
    def set_stock_warning_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_stock_warning_setting', self.of_stock_warning_setting)
