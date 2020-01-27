# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_purchase_id = fields.Many2one('purchase.order', string=u"Commande fournisseur fusionnée", copy=False, readonly=True)

    @api.depends('purchase_ids', 'of_purchase_id')
    def _compute_purchase_count(self):
        for sale_order in self:
            sale_order.purchase_count = len(sale_order.purchase_ids | sale_order.of_purchase_id)

    @api.multi
    def action_view_achats(self):
        action = self.env.ref('of_purchase.of_purchase_open_achats').read()[0]
        action['domain'] = ['|', ('sale_order_id', 'in', self._ids), ('of_sale_order_ids', 'in', self._ids)]
        return action

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    of_delivery_expected = fields.Char(string='Livraison attendue')
    of_customer_id = fields.Many2one('res.partner', string="Client")

    @api.multi
    def create(self, vals):
        purchase_order_obj = self.env['purchase.order']
        if vals.get('order_id'):
            order = purchase_order_obj.browse(vals.get('order_id'))
            if order.customer_id:
                vals['of_customer_id'] = order.customer_id.id
            if vals.get('delivery_expected'):
                vals['of_delivery_expected'] = order.delivery_expected
        return super(PurchaseOrderLine, self).create(vals)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    of_sale_order_ids = fields.One2many('sale.order', 'of_purchase_id', string=u"Commandes liées")
    of_fused = fields.Boolean(u'Commande fusionnée')
    of_sale_count = fields.Integer(compute='_compute_sale_count')

    @api.depends('of_sale_order_ids', 'sale_order_id')
    @api.multi
    def _compute_sale_count(self):
        for purchase_order in self:
            orders = purchase_order.of_sale_order_ids
            if purchase_order.sale_order_id not in orders:
                orders += purchase_order.sale_order_id
            purchase_order.of_sale_count = len(orders)

    @api.multi
    def action_view_ventes(self):
        action = self.env.ref('of_purchase_fusion.of_purchase_open_ventes').read()[0]
        action['domain'] = ['|', ('of_purchase_id', 'in', self._ids), ('purchase_ids', 'in', self._ids)]
        return action

class StockMove(models.Model):
    _inherit = 'stock.move'

    of_customer_id = fields.Many2one('res.partner', related="move_dest_id.partner_id", string="Client")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def compute_br_count(self):
        picking_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        for partner in self:
            pickings = picking_obj.search([('of_customer_id', '=', partner.id), ('of_location_usage', '=', 'supplier')])
            pickings |= move_obj.search([('of_customer_id', '=', partner.id)]).mapped('picking_id')
            partner.of_br_count = len(pickings)

    @api.multi
    def action_view_picking(self):
        picking_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        action = self.env.ref('of_purchase.of_purchase_open_picking').read()[0]
        pickings = self.env['stock.picking']
        for partner in self:
            pickings |= picking_obj.search([('of_customer_id', '=', partner.id), ('of_location_usage', '=', 'supplier')])
            pickings |= move_obj.search([('of_customer_id', '=', partner.id)]).mapped('picking_id')
        action['domain'] = [('id', 'in', pickings._ids)]
        return action
