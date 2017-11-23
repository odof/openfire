# -*- coding: utf-8 -*-

from odoo import api, fields, models

class OFKitSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _init_field_date_delivered_kit(self):
        #super(OFKitSaleOrder, self)._init_field_date_delivered()
        kits_delivered = self.env['sale.order.line'].search([('is_kit', '=', True), ('qty_delivered', '!=', 0)])
        for kit in kits_delivered:
            moves = kit.child_ids.mapped('procurement_ids').mapped('move_ids')
            if moves and all([move.state == 'done' for move in moves]):  # la ligne est entièrement livrée
                date_delivered = fields.Date.from_string(max(moves.mapped('date')))
                kit.of_date_delivered = date_delivered
                kit.child_ids.write({'of_date_delivered': date_delivered})

