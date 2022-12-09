# -*- coding: utf-8 -*-

from odoo import models, api, fields
import odoo.addons.decimal_precision as dp
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
    of_qty_available_stock = fields.Float(
        string=u"Qté stock", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_of_qty_stock')
    of_qty_virtual_stock = fields.Float(
        string=u"Qté prévisionnelle", digits=dp.get_precision('Product Unit of Measure'),
        compute='_compute_of_qty_stock')

    @api.depends('product_id')
    def _compute_of_qty_stock(self):
        for move in self:
            move.of_qty_available_stock = move.with_context(location=move.location_id.id).product_id.qty_available
            move.of_qty_virtual_stock = move.with_context(location=move.location_id.id).product_id.virtual_available

    @api.multi
    def action_assign(self, no_prepare=False):
        super(StockMove, self).action_assign(no_prepare=no_prepare)
        waiting_moves = self.filtered(lambda m: m.state in ['waiting'])
        moves_to_restart = self.env['stock.move']
        procurement_obj = self.env['procurement.order']
        if waiting_moves:
            for move in waiting_moves:
                # Si un mouvement est dans l'état "En attente d'un autre mouvement" cela signifie qu'il devrait y avoir
                # au moins un procurement.order non terminé/annulé avec comme mouvement de destination notre mouvement
                # Si ce n'est pas le cas c'est qu'il va être nécessaire de relancer l'approvisionnement
                procs = procurement_obj.search([('move_dest_id', '=', move.id), ('state', '!=', ['cancel', 'done'])])
                if not procs:
                    moves_to_restart |= move
        moves_to_restart.write({'state': 'confirmed'})

    @api.multi
    def action_reset(self):
        for move in self:
            if move.state not in ['waiting', 'assigned', 'cancel']:
                raise UserError(
                    u"Seul un mouvement en attente d'un autre mouvement, disponible ou annulé peut être réinitialisé.")
            move.linked_move_operation_ids.mapped('operation_id').unlink()
            move.quants_unreserve()
            move.write({'state': 'confirmed'})


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
