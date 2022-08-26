# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AssignManualQuants(models.TransientModel):
    _inherit = 'assign.manual.quants'

    @api.model
    def default_get(self, fields):
        res = super(AssignManualQuants, self).default_get(fields)
        move = self.env['stock.move'].browse(self.env.context['active_id'])
        available_quants = self.env['stock.quant'].search([
            ('location_id', 'child_of', move.location_id.id),
            ('product_id', '=', move.product_id.id),
            ('qty', '>', 0)
        ])
        quants_lines = [{
            'quant': x.id,
            'lot_id': x.lot_id.id,
            'in_date': x.in_date,
            'package_id': x.package_id.id,
            'selected': x in move.reserved_quant_ids,
            'qty': x.qty if x in move.reserved_quant_ids else 0,
            'location_id': x.location_id.id,
            'reservation_id': x.reservation_id.id,
            'reservation_partner_id': x.reservation_id.partner_id.id,
        } for x in available_quants]
        res.update({'quants_lines': quants_lines})
        res = self._convert_to_write(self._convert_to_cache(res))
        return res

    @api.multi
    def assign_quants(self):
        # Partie 1 : Annulation de la réservation des mouvements de stock donc on récupère les quants.
        quants_to_unreserve = self.env['stock.quant']
        links_to_remove = self.env['stock.move.operation.link']
        pack_ops_to_recompute = self.env['stock.pack.operation']
        for line in self.quants_lines.filtered('selected').filtered('reservation_id'):
            if line.reservation_id == self:
                continue
            quant = line.quant
            link = quant.reservation_id.linked_move_operation_ids.filtered(lambda l: l.reserved_quant_id == quant)
            if line.quant.qty > line.qty:
                # On découpe le quant pour conserver une partie de sa réservation actuelle
                line.quant = quant._quant_split(quant.qty - line.qty)
                # On modifie également la quantité qui lie le mouvement de stock à l'opération du BL
                if link:
                    link.qty = quant.qty
                pack_ops_to_recompute |= link.operation_id
            else:
                # On retire la réservation du quant
                quants_to_unreserve |= line.quant
                links_to_remove |= link

        if quants_to_unreserve:
            pack_ops = links_to_remove.mapped('operation_id')
            # Suppression des liens de réservation
            links_to_remove.unlink()
            # Recalcul / suppression des opérations qui ne sont plus alimentées
            pack_ops_to_recompute |= pack_ops.filtered('linked_move_operation_ids')
            pack_ops.filtered(lambda po: not po.linked_move_operation_ids).unlink()

            moves = quants_to_unreserve.mapped('reservation_id')
            # Nettoyage de la réservation des quants
            quants_to_unreserve.write({'reservation_id': False})
            # Correction de l'état des mouvements de stock
            moves.filtered(lambda m: not m.reserved_quant_ids).write({'partially_available': False})

        for pack_op in pack_ops_to_recompute:
            # On a retiré des sources à ces opérations, on recalcule donc leur quantité
            qty = sum(pack_op.linked_move_operation_ids.mapped('reserved_quant_id').mapped('qty'))
            pack_op.product_qty = pack_op.product_id.uom_id._compute_quantity(qty, pack_op.product_uom_id)
            # On repasse également les mouvements de stock "disponibles" à "en attende de disponibilité"
            pack_op.linked_move_operation_ids.mapped('move_id').write({'state': 'confirmed'})

        res = super(AssignManualQuants, self).assign_quants()

        # Partie 2 : Ajout/mise à jour des opérations pour le mouvement de stock bénéficiaire
        move = self.env['stock.move'].browse(self.env.context['active_id'])
        # Cette action recalcule toutes les opérations du bon de transfert.
        # Sur un gros bon de livraison par exemple, il serait plus efficace de ne recalculer que l'opération du
        # mouvement de stock en cours.
        move.picking_id.do_prepare_partial()
        return res


class AssignManualQuantsLines(models.TransientModel):
    _inherit = 'assign.manual.quants.lines'

    reservation_id = fields.Many2one(
        comodel_name='stock.move', string=u"Réservé par", related='quant.reservation_id', readonly=True)
    reservation_partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Partenaire", related='quant.reservation_id.partner_id', readonly=True)
