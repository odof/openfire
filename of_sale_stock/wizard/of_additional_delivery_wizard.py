# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import Warning


class OFAdditionalDeliveryWizard(models.TransientModel):
    _name = 'of.additional.delivery.wizard'
    _description = "Assistant de création de bon de livraison complémentaire"

    picking_id = fields.Many2one(comodel_name='stock.picking', string=u"Bon de livraison d'originie")
    line_ids = fields.One2many(
        comodel_name='of.additional.delivery.wizard.line', inverse_name='wizard_id', string=u"Lignes à diviser")

    @api.multi
    def action_additional_delivery(self):
        self.ensure_one()

        # On vérifie qu'il y ait des quantités à créer
        lines = self.line_ids.filtered(lambda line: line.qty > 0)
        with self.env.norecompute():
            # On copie le Bon de transfert (sans les mouvements)
            new_picking = self.picking_id.copy(
                {'move_lines': [], 'backorder_id': self.picking_id.id})
            new_picking.onchange_picking_type()

            # On met à jour les lignes du nouveau Bon de transfert
            for line in lines:
                if not line.qty:
                    # Pas de qté, pas besoin de copier
                    continue
                else:
                    # On copie le mouvement pour le nouveau transfert avec les nouvelles qtés
                    line.move_id.copy(
                        {'picking_id': new_picking.id,
                        'location_id': new_picking.location_id.id,
                        'location_dest_id': new_picking.location_dest_id.id,
                        'picking_type_id': new_picking.picking_type_id.id,
                        'product_uom_qty': line.qty,
                        'of_ordered_qty': line.qty,
                        'state': 'draft'})

        self.recompute()

        # On renvoie sur le nouveau Bon de transfert
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
        action['res_id'] = new_picking.id

        return action


class OFDeliveryDivisionWizardLine(models.TransientModel):
    _name = 'of.additional.delivery.wizard.line'
    _description = "Ligne de l'assistant de division des Bon de transfert"

    wizard_id = fields.Many2one(comodel_name='of.additional.delivery.wizard', string=u"Bon de transfert complémentaire")
    move_id = fields.Many2one(comodel_name='stock.move', string=u"Ligne du Bon de transfert")
    product_id = fields.Many2one(
        comodel_name='product.product', related='move_id.product_id', string=u"Référence article", readonly=True)
    name = fields.Char(string=u"Description", related='move_id.name', readonly=True)
    qty = fields.Float(string=u"Quantité")
