# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class StockReservation(models.Model):
    _inherit = 'stock.reservation'

    of_sale_line_id = fields.Many2one(
        comodel_name='sale.order.line', string=u"Ligne de commande", ondelete='cascade', copy=False)
    of_sale_order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", compute='_compute_order_fields')
    of_sale_partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"partenaire", compute='_compute_order_fields')

    @api.depends('of_sale_line_id')
    def _compute_order_fields(self):
        for record in self:
            record.of_sale_order_id = record.of_sale_line_id.order_id
            record.of_sale_partner_id = record.of_sale_line_id.order_id.partner_id

    @api.model
    def _default_picking_type_id(self):
        return self.env.ref('of_stock_reserve_sale.picking_type_reserve', raise_if_not_found=False).id
