# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_expected = fields.Char(string='Livraison attendue', states={'done': [('readonly', True)]})
    purchase_ids = fields.One2many("purchase.order", "sale_order_id", string="Achats")
    purchase_count = fields.Integer(compute='_compute_purchase_count')
    of_user_id = fields.Many2one(comodel_name='res.users', string="Responsable technique")

    @api.depends('purchase_ids')
    @api.multi
    def _compute_purchase_count(self):
        for sale_order in self:
            sale_order.purchase_count = len(sale_order.purchase_ids)

    @api.multi
    def action_view_achats(self):
        action = self.env.ref('of_purchase.of_purchase_open_achats').read()[0]
        action['domain'] = [('sale_order_id', 'in', self._ids)]
        return action
