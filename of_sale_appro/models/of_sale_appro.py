# -*- coding: utf-8 -*-

from odoo import models, api

from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def button_create_procurement(self):
        procurements = self.env['procurement.order']
        for move in self:
            if move.state != 'confirmed':
                raise UserError(u"Seul un mouvement en attente de disponibilitré peut être approvisionné.")

            # Code copié depuis stock.move.action_confirm()
            # create procurements for make to order moves
            procurements |= procurements.create(move._prepare_procurement_from_move())
        if procurements:
            procurements.run()

        self.write({'state': 'waiting'})
