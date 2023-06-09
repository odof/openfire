# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class OFStockReserveSaleWizard(models.TransientModel):
    _name = 'of.stock.reserve.sale.wizard'

    @api.model
    def default_get(self, fields_list):
        result = super(OFStockReserveSaleWizard, self).default_get(fields_list)
        if self._context.get('active_model') == 'sale.order.line' and self._context.get('active_id'):
            order_line = self.env['sale.order.line'].browse(self._context.get('active_id'))
            result['order_line_id'] = order_line.id
            result['product_id'] = order_line.product_id.id
            result['qty_ordered'] = order_line.product_uom_qty
            result['qty_unreserved'] = order_line.of_qty_unreserved
            result['line_ids'] = []

            quants = self.env['stock.quant'].search([
                ('product_id', '=', order_line.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('location_id.company_id', '=', order_line.order_id.company_id.id),
                ('reservation_id', '=', False)])
            locations = quants.mapped('location_id')
            for loc in locations:
                serials = quants.filtered(lambda q: q.location_id == loc).mapped('lot_id')
                for serial in serials:
                    qty = sum(quants.filtered(lambda q: q.location_id == loc and q.lot_id == serial).mapped('qty'))
                    result['line_ids'] += [
                        (0, 0, {'location_id': loc.id,
                                'of_internal_serial_number': serial.of_internal_serial_number or u"Aucun numéro",
                                'qty_available': qty,
                                'qty_to_reserve': 0})]
                qty = sum(quants.filtered(lambda q: q.location_id == loc and not q.lot_id).mapped('qty'))
                if qty > 0:
                    result['line_ids'] += [(0, 0, {'location_id': loc.id, 'qty_available': qty, 'qty_to_reserve': 0})]

        return result

    order_line_id = fields.Many2one(comodel_name='sale.order.line', string=u"Ligne de commande associée")
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article")
    qty_ordered = fields.Float(string=u"Quantité commandée", digits=dp.get_precision('Product Unit of Measure'))
    qty_unreserved = fields.Float(string=u"Quantité non réservée", digits=dp.get_precision('Product Unit of Measure'))
    line_ids = fields.One2many(
        comodel_name='of.stock.reserve.sale.wizard.line',inverse_name='wizard_id', string=u"Lignes de stock")
    date_validity = fields.Date(
        string=u"Date de validité", help=u"Si renseignée, la réservation sera annulée après cette date.")

    @api.multi
    def _prepare_stock_reservation(self, line):
        self.ensure_one()
        return {'product_id': self.product_id.id,
                'product_uom': self.order_line_id.product_uom.id,
                'product_uom_qty': line.qty_to_reserve,
                'date_validity': self.date_validity,
                'name': "%s (%s)" % (self.order_line_id.order_id.name, self.product_id.name),
                'location_id': line.location_id.id,
                'location_dest_id': self.env.ref('stock_reserve.stock_location_reservation').id,
                'picking_type_id': self.env.ref('of_stock_reserve_sale.picking_type_reserve').id,
                'group_id': self.order_line_id.order_id.of_reserv_proc_group_id.id,
                'of_sale_line_id': self.order_line_id.id,
                }

    @api.multi
    def action_reserve(self):
        self.ensure_one()

        if self.line_ids.filtered(lambda l: l.qty_to_reserve < 0):
            raise UserError(u"Vous ne pouvez pas saisir de quantité négative.")

        if self.line_ids.filtered(lambda l: l.qty_to_reserve > 0 and l.qty_to_reserve > l.qty_available):
            raise UserError(u"Vous ne pouvez pas saisir une quantité supérieure à la quantité disponible.")

        total_qty = sum(self.line_ids.mapped('qty_to_reserve'))
        if total_qty > self.qty_unreserved:
            raise UserError(u"Vous ne pouvez pas saisir une quantité supérieure à la quantité non réservée.")

        if self.line_ids.filtered(lambda l: l.qty_to_reserve > 0):
            if not self.order_line_id.order_id.of_reserv_proc_group_id:
                proc_group = self.env['procurement.group'].create(
                    {'name': u"%s (Réservation)" % self.order_line_id.order_id.name})
                self.order_line_id.order_id.of_reserv_proc_group_id = proc_group
            for line in self.line_ids.filtered(lambda l: l.qty_to_reserve > 0):
                vals = self._prepare_stock_reservation(line)
                reservation = self.env['stock.reservation'].create(vals)
                reservation.reserve()

        return True


class OFStockReserveSaleWizardLine(models.TransientModel):
    _name = 'of.stock.reserve.sale.wizard.line'

    wizard_id = fields.Many2one(comodel_name='of.stock.reserve.sale.wizard', string=u"Wizard")
    location_id = fields.Many2one(comodel_name='stock.location', string=u"Emplacement")
    of_internal_serial_number = fields.Char(string=u"Numéro de série interne")
    qty_available = fields.Float(string=u"Quantité disponible", digits=dp.get_precision('Product Unit of Measure'))
    qty_to_reserve = fields.Float(string=u"Quantité à réserver", digits=dp.get_precision('Product Unit of Measure'))
