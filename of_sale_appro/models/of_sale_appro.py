# -*- coding: utf-8 -*-

from odoo import models, api, fields

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

    # Par défaut les champs relationnels sont lus en tant qu'admin.
    # Ici ce ne doit pas être le cas car les quantités doivent êtres lues dans la société de l'utilisateur
    of_qty_available_stock = fields.Float(string=u"Qté stock", related="product_id.qty_available", related_sudo=False)
    of_qty_virtual_stock = fields.Float(string=u"Qté stock", related="product_id.virtual_available", related_sudo=False)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_procure_all(self):
        self.move_lines.filtered(lambda m: m.state in ['confirmed']).button_create_procurement()
        if bool(self.move_lines.filtered(lambda m: m.state in ['draft', 'confirmed', 'partially_available'])):
            message = u"Certaines lignes n'ont pas pu être approvisionnées."
        else:
            message = u"Toutes les lignes ont bien été approvisionnées."
        return self.env['of.popup.wizard'].popup_return(message)
