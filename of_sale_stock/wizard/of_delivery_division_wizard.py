# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import Warning


class OFDeliveryDivisionWizard(models.TransientModel):
    _name = 'of.delivery.division.wizard'
    _description = "Assistant de division des BL"

    picking_id = fields.Many2one(comodel_name='stock.picking', string=u"BL à diviser")
    line_ids = fields.One2many(
        comodel_name='of.delivery.division.wizard.line', inverse_name='wizard_id', string=u"Lignes à diviser")

    @api.multi
    def action_delivery_division(self):
        self.ensure_one()

        # On vérifie qu'il y ait des quantités à diviser
        if not self.line_ids.filtered(lambda line: line.qty_to_divide > 0):
            raise Warning(u"Vous n'avez saisi aucune quantité à diviser !")
        elif self.line_ids.filtered(lambda line: line.qty_to_divide > line.product_uom_qty):
            raise Warning(u"Vous avez saisi trop de quantité à diviser par rapport à la quantité initiale !")
        elif self.line_ids.filtered(lambda line: line.qty_to_divide < 0):
            raise Warning(u"Vous avez saisi des quantités négatives !")
        else:
            # On copie le BL
            new_delivery = self.picking_id.copy()

            # On met à jour les lignes des 2 BL
            for line_to_divide in self.line_ids:
                if line_to_divide.qty_to_divide == 0:
                    # On supprime la ligne du nouveau BL
                    line_to_delete = new_delivery.move_lines.filtered(
                        lambda line: line.procurement_id == line_to_divide.move_id.procurement_id)
                    line_to_delete.action_cancel()
                    line_to_delete.unlink()
                else:
                    initial_qty = line_to_divide.product_uom_qty - line_to_divide.qty_to_divide
                    if initial_qty == 0:
                        # On supprime la ligne du BL initial
                        line_to_divide.move_id.action_cancel()
                        line_to_divide.move_id.unlink()
                    else:
                        # On diminue les quantités de la ligne d'origine
                        line_to_divide.move_id.write({'product_uom_qty': initial_qty,
                                                      'of_ordered_qty': initial_qty})
                        # On diminue les quantités de la nouvelle ligne
                        new_delivery.move_lines.filtered(
                            lambda line: line.procurement_id == line_to_divide.move_id.procurement_id).\
                            write({'product_uom_qty': line_to_divide.qty_to_divide,
                                   'of_ordered_qty': line_to_divide.qty_to_divide})

            self.picking_id.action_assign()
            new_delivery.action_assign()

            # On renvoie sur le nouveau BL
            action = self.env.ref('stock.action_picking_tree_all').read()[0]
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = new_delivery.id

        return action


class OFDeliveryDivisionWizardLine(models.TransientModel):
    _name = 'of.delivery.division.wizard.line'
    _description = "Ligne de l'assistant de division des BL"

    wizard_id = fields.Many2one(comodel_name='of.delivery.division.wizard', string=u"Division du BL")
    move_id = fields.Many2one(comodel_name='stock.move', string=u"Ligne du BL")
    product_id = fields.Many2one(
        comodel_name='product.product', related='move_id.product_id', string=u"Article", readonly=True)
    product_uom_qty = fields.Float(related='move_id.product_uom_qty', string=u"Quantité initiale", readonly=True)
    qty_to_divide = fields.Float(string=u"Quantité à diviser")
