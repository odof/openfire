# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_customer_id = fields.Many2one('res.partner', string="Client")
    of_customer_shipping_id = fields.Many2one('res.partner', string=u"Adresse de Livraison du Client")
    of_customer_shipping_city = fields.Char(
        related='of_customer_shipping_id.city', string=u"Ville", store=True, readonly=True, compute_sudo=True)
    of_customer_shipping_zip = fields.Char(
        related='of_customer_shipping_id.zip', string=u"Code Postal", store=True, readonly=True, compute_sudo=True)
    partner_shipping_id = fields.Many2one('res.partner', string=u"Adresse de Livraison du Partenaire")
    partner_shipping_city = fields.Char(
        related='partner_shipping_id.city', string=u"Ville", store=True, readonly=True, compute_sudo=True)
    partner_shipping_zip = fields.Char(
        related='partner_shipping_id.zip', string=u"Code Postal", store=True, readonly=True, compute_sudo=True)
    # Permet de cacher le champ of_customer_id si pas sur BR
    of_location_usage = fields.Selection(related="location_id.usage")
    of_user_id = fields.Many2one(comodel_name='res.users', string="Responsable technique")

    @api.onchange('of_customer_id')
    def _onchange_of_customer_id(self):
        self.ensure_one()
        addresses = self.of_customer_id.address_get(['delivery'])
        self.of_customer_shipping_id = addresses['delivery']

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.ensure_one()
        addresses = self.partner_id.address_get(['delivery'])
        self.partner_shipping_id = addresses['delivery']


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_procurement_purchase_id = fields.Many2one(comodel_name='purchase.order',
        string="Commande d'achat lié", compute='_compute_of_procurement_purchase_id')
    of_procurement_purchase_line_id = fields.Many2one(comodel_name='purchase.order.line',
        string="Ligne de commande d'achat lié", compute='_compute_of_procurement_purchase_line_id', store=True)
    of_check = fields.Boolean(string="Contrôle", compute='_compute_of_check', store=True)

    @api.depends('state', 'group_id', 'picking_type_id')
    def _compute_of_procurement_purchase_line_id(self):
        sale_order_obj = self.env['sale.order']
        purchase_order_obj = self.env['purchase.order']
        for move in self.filtered(lambda m: m.picking_type_id.code == 'outgoing'):
            sale_order = sale_order_obj.search(
                [('name', '=', move.group_id.name), ('partner_id', '=', move.partner_id.id)])
            if sale_order:
                purchase_orders = purchase_order_obj.search([('sale_order_id', '=', sale_order.id)])
                purchase_order_lines = purchase_orders.mapped('order_line').filtered(
                    lambda pol: pol.product_id == move.product_id)
                if purchase_order_lines:
                    move.of_procurement_purchase_line_id = purchase_order_lines[0].id

    @api.depends('of_procurement_purchase_line_id')
    def _compute_of_procurement_purchase_id(self):
        for move in self.filtered(lambda m: m.of_procurement_purchase_line_id):
            move.of_procurement_purchase_id = move.of_procurement_purchase_line_id.order_id.id

    @api.depends('of_procurement_purchase_line_id', 'reserved_quant_ids')
    def _compute_of_check(self):
        stock_move_obj = self.env['stock.move']
        for move in self.filtered(lambda m: m.of_procurement_purchase_line_id):
            purchase_stock_move = stock_move_obj.search(
                [('purchase_line_id', '=', move.of_procurement_purchase_line_id.id), ('purchase_line_id', '!=', False)])
            if purchase_stock_move:
                move.of_check = any(quant.id in move.reserved_quant_ids.ids for quant in purchase_stock_move.mapped(
                    'quant_ids'))
            else:
                move.of_check = False

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if isinstance(res, dict):
            responsable = self.mapped('procurement_id').mapped('sale_line_id').mapped('order_id').mapped('of_user_id')
            if len(responsable) == 1:
                res['of_user_id'] = responsable.id
        return res
