# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
