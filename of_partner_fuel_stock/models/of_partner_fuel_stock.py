# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class OFResPartnerFuelStock(models.Model):
    _name = 'of.res.partner.fuel.stock'
    _description = u"""État de stock combustible des clients"""
    _order = 'partner_id'

    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Client", required=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article de combustible", required=True)
    ordered_qty = fields.Float(string=u"Quantité commandée")
    checkout_qty = fields.Float(string=u"Quantité retirée")
    balance = fields.Float(string=u"Solde", compute='_compute_balance', search='_search_balance')
    order_ids = fields.Many2many(comodel_name='sale.order', string=u"Commandes", compute='_compute_orders')
    order_count = fields.Integer(string=u"Nombre de commandes", compute='_compute_orders')
    picking_ids = fields.Many2many(comodel_name='stock.picking', string=u"Enlèvements", compute='_compute_pickings')
    picking_count = fields.Integer(string=u"Nombre d'enlèvements'", compute='_compute_pickings')

    _sql_constraints = [
        ('partner_product_uniq',
         'unique (partner_id, product_id)',
         u"Un état de stock existe déjà pour ce client et cet article.")
    ]

    @api.depends('ordered_qty', 'checkout_qty')
    def _compute_balance(self):
        for fuel_stock in self:
            fuel_stock.balance = fuel_stock.ordered_qty - fuel_stock.checkout_qty

    @api.model
    def _search_balance(self, operator, value):
        fuel_stocks = self.search([]).filtered(lambda rec: safe_eval("value %s %s" %
                                                                     (operator if operator != '=' else '==', value),
                                                                     {'value': rec.ordered_qty - rec.checkout_qty}))
        return [('id', 'in', fuel_stocks.ids)]

    def _compute_orders(self):
        for fuel_stock in self:
            partner_orders = self.env['sale.order'].search([('partner_id', '=', self.partner_id.id)])
            orders = partner_orders.mapped('order_line').filtered(
                lambda l: l.of_storage and
                (l.product_id == self.product_id or
                 (l.of_is_kit and
                  l.kit_id.kit_line_ids.mapped('product_id').filtered(lambda p: p == self.product_id)))).\
                mapped('order_id')
            fuel_stock.order_ids = orders
            fuel_stock.order_count = len(orders.filtered(lambda o: o.state in ('sale', 'done')))

    def _compute_pickings(self):
        for fuel_stock in self:
            partner_pickings = self.env['stock.picking'].search(
                [('partner_id', '=', self.partner_id.id), ('of_storage', '=', True)])
            pickings = partner_pickings.mapped('move_lines').filtered(
                lambda l: l.product_id == self.product_id).mapped('picking_id').filtered(lambda o: o.state != 'cancel')
            fuel_stock.picking_ids = pickings
            fuel_stock.picking_count = len(pickings.filtered(lambda p: p.state == 'done'))

    @api.multi
    def name_get(self):
        return [(record.id, "%s - %s" % (record.partner_id.name, record.product_id.name)) for record in self]

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(OFResPartnerFuelStock, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                            orderby=orderby, lazy=lazy)
        for line in res:
            if 'balance' in fields:
                line['balance'] = line['ordered_qty'] - line['checkout_qty']

        return res

    @api.multi
    def action_view_orders(self):
        action = self.env.ref('sale.action_orders').read()[0]

        action['domain'] = [('id', 'in', self.order_ids.ids)]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context.update({
                'default_partner_id': self.partner_id.id
            })
            action['context'] = str(context)

        return action

    @api.multi
    def action_view_pickings(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        if len(self._ids) == 1:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing'), ('warehouse_id', '=', warehouse.id)], limit=1)
            context = safe_eval(action['context'])
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_picking_type_id': picking_type.id,
                'default_of_storage': True,
            })
            action['context'] = str(context)

        return action
