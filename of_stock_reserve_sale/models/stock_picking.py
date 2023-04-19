# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_sale_reservation_count = fields.Integer(
        string=u"Nombre de réservations ventes", compute='_compute_of_sale_reservation_count')

    @api.multi
    @api.depends('move_lines.procurement_id.sale_line_id.of_reservation_ids')
    def _compute_of_sale_reservation_count(self):
        for picking in self:
            picking.of_sale_reservation_count = len(
                picking.move_lines.mapped('procurement_id.sale_line_id.of_reservation_ids'))

    @api.multi
    def action_view_reservations(self):
        action = self.env.ref('stock_reserve.action_stock_reservation_tree').read()[0]

        reservations = self.mapped('move_lines.procurement_id.sale_line_id.of_reservation_ids')
        if len(reservations) > 1:
            action['domain'] = [('id', 'in', reservations.ids)]
        elif reservations:
            action['views'] = [(self.env.ref('stock_reserve.view_stock_reservation_form').id, 'form')]
            action['res_id'] = reservations.id
        return action
