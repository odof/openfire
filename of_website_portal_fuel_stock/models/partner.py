# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_fuel_stock_ids = fields.Many2many(
        comodel_name='product.product', string=u"Stocks de combustible", compute='_compute_of_fuel_stocks')
    of_fuel_stock_count = fields.Integer(
        string=u"Nombre de stocks de combustible", compute='_compute_of_fuel_stocks')

    @api.multi
    def _compute_of_fuel_stocks(self):
        for partner in self:
            stock_fuel_product_ids = self.env['of.res.partner.fuel.stock'].search([('partner_id', '=', partner.id)]).\
                mapped('product_id')
            partner.of_fuel_stock_ids = stock_fuel_product_ids
            partner.of_fuel_stock_count = len(stock_fuel_product_ids)

    @api.multi
    def get_fuel_balance(self, product):
        self.ensure_one()
        return self.env['of.res.partner.fuel.stock'].search(
            [('partner_id', '=', self.id), ('product_id', '=', product.id)], limit=1).balance

    @api.multi
    def get_fuel_purchase_qty(self, product):
        self.ensure_one()
        return self.env['of.res.partner.fuel.stock'].search(
            [('partner_id', '=', self.id), ('product_id', '=', product.id)], limit=1).ordered_qty

    @api.multi
    def get_fuel_checkout_qty(self, product):
        self.ensure_one()
        return self.env['of.res.partner.fuel.stock'].search(
            [('partner_id', '=', self.id), ('product_id', '=', product.id)], limit=1).checkout_qty

    @api.multi
    def get_checkouts(self, product):
        self.ensure_one()
        return self.env['of.res.partner.fuel.stock'].\
            search([('partner_id', '=', self.id), ('product_id', '=', product.id)], limit=1).picking_ids.\
            filtered(lambda p: p.state == 'done')
