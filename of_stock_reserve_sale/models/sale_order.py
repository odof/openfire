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

    @api.multi
    def action_confirm(self):
        auto_reserve = self.env['ir.values'].get_default('stock.config.settings', 'of_auto_reserve')
        res = super(SaleOrder, self).action_confirm()
        if auto_reserve:
            lines_to_process = self.mapped('order_line').filtered('of_reservation_ids')
            # Check locations to determine if division is necessary
            default_picking = lines_to_process.mapped('procurement_ids.move_ids.picking_id')
            if default_picking and len(default_picking) > 1:
                default_picking = default_picking[0]
            default_location = default_picking.picking_type_id.default_location_src_id
            locations = lines_to_process.mapped('of_reservation_ids.reserved_quant_ids.location_id')
            division_dict = {}
            for location in locations.filtered(lambda loc: loc.id != default_location.id):
                division_dict[location.id] = {}
                for line in lines_to_process:
                    qty_to_divide = 0
                    for quant in line.of_reservation_ids.mapped('reserved_quant_ids'):
                        if quant.location_id.id == location.id:
                            qty_to_divide += quant.qty
                    if qty_to_divide:
                        division_dict[location.id][line] = qty_to_divide
            # Picking division
            picking_type_obj = self.env['stock.picking.type']
            delivery_division_wizard_obj = self.env['of.delivery.division.wizard']
            for location_id, lines_dict in division_dict.iteritems():
                picking_type = picking_type_obj.search(
                    [('code', '=', 'outgoing'), ('default_location_src_id', '=', location_id)], limit=1)
                line_vals = []
                for line, qty_to_divide in lines_dict.iteritems():
                    move = line.mapped(
                        'procurement_ids.move_ids').filtered(lambda move: move.picking_id.id == default_picking.id)
                    line_vals.append((0, 0, {'move_id': move.id, 'qty_to_divide': qty_to_divide}))
                wizard = delivery_division_wizard_obj.create({
                    'picking_id': default_picking.id,
                    'line_ids': line_vals,
                    'picking_type_id': picking_type.id
                })
                wizard.action_delivery_division()
            # Reservation
            for line in lines_to_process:
                for quant in line.mapped('of_reservation_ids.reserved_quant_ids'):
                    move = line.procurement_ids.mapped('move_ids').filtered(
                        lambda m: m.location_id.id == quant.location_id.id)
                    quant.reservation_id.action_cancel()
                    move.reservation_to_operation(quant)
        return res


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
