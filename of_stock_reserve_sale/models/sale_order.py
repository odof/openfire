# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_reserv_proc_group_id = fields.Many2one(
        comodel_name='procurement.group', string=u"Groupe d'approvisionnement de réservation", copy=False)
    of_reservation_count = fields.Integer(string=u"Nombre de réservations", compute='_compute_of_reservation_count')

    @api.multi
    @api.depends('order_line.of_reservation_ids')
    def _compute_of_reservation_count(self):
        for order in self:
            order.of_reservation_count = len(order.mapped('order_line.of_reservation_ids'))

    @api.multi
    def action_view_reservations(self):
        action = self.env.ref('stock_reserve.action_stock_reservation_tree').read()[0]

        reservations = self.mapped('order_line.of_reservation_ids')
        if len(reservations) > 1:
            action['domain'] = [('id', 'in', reservations.ids)]
        elif reservations:
            action['views'] = [(self.env.ref('stock_reserve.view_stock_reservation_form').id, 'form')]
            action['res_id'] = reservations.id
        return action

    @api.multi
    def action_cancel(self):
        self.mapped('order_line').release_stock_reservations()
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def action_done(self):
        self.mapped('order_line').release_stock_reservations()
        return super(SaleOrder, self).action_done()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_reservation_ids = fields.One2many(
        comodel_name='stock.reservation', inverse_name='of_sale_line_id', string=u"Pré-réservations internes",
        copy=False)
    of_qty_unreserved = fields.Float(
        string=u"Quantité non réservée", compute='_compute_of_qty_unreserved',
        digits=dp.get_precision('Product Unit of Measure'))

    @api.depends(
        'of_reservation_ids', 'of_reservation_ids.state', 'of_reservation_ids.product_uom_qty', 'product_uom_qty')
    def _compute_of_qty_unreserved(self):
        for line in self:
            qty_reserved = sum(
                line.of_reservation_ids.filtered(lambda r: r.state == 'assigned').mapped('product_uom_qty'))
            line.of_qty_unreserved = line.product_uom_qty - qty_reserved

    @api.multi
    def unlink(self):
        self.release_stock_reservations()
        return super(SaleOrderLine, self).unlink()

    @api.multi
    def release_stock_reservations(self):
        self.mapped('of_reservation_ids').release()
        return True
