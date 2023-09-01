# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def reservation_to_operation(self, base_quants):
        # Fonction basée sur la réservation manuelle, adaptée pour fonctionner avec la pré-réservation
        quant_obj = self.env['stock.quant']
        pickings_to_recompute = self.env['stock.picking'].sudo()
        for move in self:
            # Remettre a 0 pour ne pas refaire les opérations sur des mouvements où ce ne serait pas nécessaire
            quants_to_unreserve = self.env['stock.quant'].sudo()
            links_to_remove = self.env['stock.move.operation.link']
            pack_ops_to_recompute = self.env['stock.pack.operation']
            quants_used = self.env['stock.quant'].sudo()
            # On sépare les qtés avec réservation de celle sans, on préfère n'utiliser que celles sans réservation si
            # possible
            reserved_quants = base_quants.filtered('reservation_id')
            quants_to_use = base_quants.filtered(lambda q: not q.reservation_id)
            if sum(quants_to_use.mapped('qty')) < move.product_qty:
                # On doit utiliser celles qui sont déjà réservées
                rest = move.product_qty - sum(quants_to_use.mapped('qty'))
                for quant in reserved_quants:
                    if rest <= 0:
                        break
                    link = quant.reservation_id.linked_move_operation_ids.filtered(
                        lambda l: l.reserved_quant_id == quant)
                    if quant.qty > rest:
                        # On découpe le quant pour conserver une partie de sa réservation actuelle
                        new_quant = quant._quant_split(rest)
                        quants_to_use += new_quant
                        rest -= new_quant.qty
                        # On modifie également la quantité qui lie le mouvement de stock à l'opération du BL
                        if link:
                            link.qty = quant.qty
                        pack_ops_to_recompute |= link.operation_id
                    else:
                        # On retire la réservation du quant
                        rest -= quant.qty
                        quants_to_use += quant
                        reserved_quants -= quant
                        quants_to_unreserve |= quant
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

            if quants_to_use:
                quants = []
                if move.picking_id:
                    pickings_to_recompute |= move.picking_id
                for quant_id in move.reserved_quant_ids.ids:
                    move.write({'reserved_quant_ids': [[3, quant_id]]})
                rest_quant = False
                for quant in quants_to_use:
                    if sum([q[1] for q in quants]) >= move.product_qty:
                        break
                    if sum([q[1] for q in quants]) + quant.qty > move.product_qty:
                        rest_quant = quant._quant_split(quant.qty - rest)
                    quants_used |= quant
                    quants.append((quant, quant.qty))
                if quants:
                    quant_obj.quants_reserve(quants, move)
            # Partie 2 : Ajout/mise à jour des opérations pour le mouvement de stock bénéficiaire
            # Cette action recalcule toutes les opérations du bon de transfert.
            # Sur un gros bon de livraison par exemple, il serait plus efficace de ne recalculer que l'opération du
            # mouvement de stock en cours.
            base_quants = reserved_quants + quants_to_use - quants_used
            if rest_quant:
                base_quants += rest_quant
        if pickings_to_recompute:
            pickings_to_recompute.mapped('pack_operation_ids').unlink()
            pickings_to_recompute.write({'recompute_pack_op': True})
            for picking in pickings_to_recompute:
                picking.do_prepare_partial()
        return base_quants
