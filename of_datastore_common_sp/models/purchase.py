# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    of_datastore_anomalie = fields.Boolean(
        string="En anomalie", compute='_compute_of_datastore_anomalie', search="_search_of_datastore_anomalie")

    @api.depends('picking_ids', 'picking_ids.of_datastore_anomalie')
    def _compute_of_datastore_anomalie(self):
        for purchase in self:
            purchase.of_datastore_anomalie = any(purchase.picking_ids.mapped('of_datastore_anomalie'))

    @api.model
    def _search_of_datastore_anomalie(self, operator, value):
        orders = self.env['stock.picking'].search([('of_datastore_anomalie', operator, value)]) \
            .mapped('move_lines') \
            .mapped('procurement_id') \
            .mapped('purchase_line_id') \
            .mapped('order_id')
        return [('id', 'in', orders.ids)]
