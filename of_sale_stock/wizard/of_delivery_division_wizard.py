# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import Warning
from odoo.tools.float_utils import float_is_zero


class OFDeliveryDivisionWizard(models.TransientModel):
    _name = 'of.delivery.division.wizard'
    _description = "Assistant de division de bon de transfert"

    picking_type_id = fields.Many2one(comodel_name='stock.picking.type', string=u"Type de préparation", required=True)
    picking_id = fields.Many2one(comodel_name='stock.picking', string=u"Bon de transfert à diviser")
    line_ids = fields.One2many(
        comodel_name='of.delivery.division.wizard.line', inverse_name='wizard_id', string=u"Lignes à diviser")
    locked_lines = fields.Boolean(compute='_compute_locked_lines')

    @api.depends('line_ids', 'line_ids.state')
    def _compute_locked_lines(self):
        for wiz in self:
            wiz.locked_lines = any(line.state == 'assigned' for line in wiz.line_ids)

    @api.multi
    def action_delivery_division(self):
        self.ensure_one()

        # On vérifie qu'il y ait des quantités à diviser
        lines = self.line_ids.filtered(lambda line: line.qty_to_divide > 0)
        if not lines:
            raise Warning(u"Vous n'avez saisi aucune quantité à diviser !")
        elif any(line.qty_to_divide > line.product_uom_qty for line in lines):
            raise Warning(u"Vous avez saisi trop de quantité à diviser par rapport à la quantité initiale !")
        elif any(line.qty_to_divide < 0 for line in self.line_ids):
            raise Warning(u"Vous avez saisi des quantités négatives !")
        else:
            with self.env.norecompute():
                # On copie le Bon de transfert (sans les mouvements)
                new_picking = self.picking_id.copy(
                    {'picking_type_id': self.picking_type_id.id, 'move_lines': []})
                new_picking.onchange_picking_type()

                # On met à jour les lignes des 2 Bons de transfert
                moves_to_move = self.env['stock.move']
                for line_to_divide in lines:
                    initial_qty = line_to_divide.product_uom_qty - line_to_divide.qty_to_divide
                    if float_is_zero(initial_qty, precision_rounding=line_to_divide.product_id.uom_id.rounding):
                        moves_to_move += line_to_divide.move_id
                    else:
                        # On copie le mouvement pour le nouveau transfert
                        new_move = line_to_divide.move_id.copy(
                            {'picking_id': new_picking.id,
                             'location_id': new_picking.location_id.id,
                             'location_dest_id': new_picking.location_dest_id.id,
                             'picking_type_id': self.picking_type_id.id,
                             'product_uom_qty': line_to_divide.qty_to_divide,
                             'of_ordered_qty': line_to_divide.qty_to_divide,
                             'warehouse_id': self.picking_type_id.warehouse_id.id})
                        # On marque le nouveau mouvement "à faire"
                        new_move.action_confirm()
                        # On diminue les quantités du mouvement d'origine
                        line_to_divide.move_id.write(
                            {'product_uom_qty': initial_qty, 'of_ordered_qty': initial_qty})

                # On déplace les mouvements vers le nouveau transfert
                moves_to_move.write(
                    {'picking_id': new_picking.id,
                     'location_id': new_picking.location_id.id,
                     'location_dest_id': new_picking.location_dest_id.id,
                     'picking_type_id': self.picking_type_id.id,
                     'warehouse_id': self.picking_type_id.warehouse_id.id})

                if self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'procurement_jit'), ('state', 'in', ('installed', 'to install', 'to upgrade'))]):
                    self.picking_id.action_assign()
                    new_picking.action_assign()

            self.recompute()

            # On renvoie sur le nouveau Bon de transfert
            action = self.env.ref('stock.action_picking_tree_all').read()[0]
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = new_picking.id

        return action


class OFDeliveryDivisionWizardLine(models.TransientModel):
    _name = 'of.delivery.division.wizard.line'
    _description = "Ligne de l'assistant de division des Bon de transfert"

    wizard_id = fields.Many2one(comodel_name='of.delivery.division.wizard', string=u"Division du Bon de transfert")
    move_id = fields.Many2one(comodel_name='stock.move', string=u"Ligne du Bon de transfert")
    product_id = fields.Many2one(
        comodel_name='product.product', related='move_id.product_id', string=u"Référence article", readonly=True)
    name = fields.Char(string=u"Description", related='move_id.name', readonly=True)
    product_uom_qty = fields.Float(related='move_id.product_uom_qty', string=u"Quantité initiale", readonly=True)
    qty_to_divide = fields.Float(string=u"Quantité à diviser")
    qty_available = fields.Float(string=u"Stock disponible", compute='_compute_qty_available', store=True)
    state = fields.Selection(related='move_id.state', readonly=True)

    @api.depends('wizard_id.picking_type_id')
    def _compute_qty_available(self):
        quant_obj = self.env['stock.quant']
        for line in self:
            quants = quant_obj.search(
                [('product_id', '=', line.product_id.id),
                 ('location_id', '=', line.wizard_id.picking_type_id.default_location_src_id.id)])
            line.qty_available = sum(quants.mapped('qty'))
