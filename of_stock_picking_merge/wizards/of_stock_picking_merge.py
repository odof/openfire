# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFStockPickingMerge(models.TransientModel):
    _name = 'of.stock.picking.merge'
    _description = u"Assistant de fusion pour les opérations de stock"

    @api.model
    def default_get(self, fields):
        result = super(OFStockPickingMerge, self).default_get(fields)
        if self._context.get('active_model') == 'stock.picking' and self._context.get('active_ids'):
            pickings = self.env['stock.picking'].browse(self._context.get('active_ids'))

            if len(pickings) <= 1:
                result['info_txt'] = u"Il faut sélectionner plusieurs opérations pour une fusion !"
                result['error'] = True
                return result

            if len(pickings.mapped('picking_type_id')) > 1:
                result['info_txt'] = u"Toutes les opérations à fusionner doivent être de même type !"
                result['error'] = True
                return result

            if len(pickings.mapped('location_id')) > 1 or len(pickings.mapped('location_dest_id')) > 1:
                result['info_txt'] = \
                    u"Toutes les opérations à fusionner doivent avoir les mêmes emplacements source et destination !"
                result['error'] = True
                return result

            if len(pickings.mapped('partner_id')) > 1:
                result['info_txt'] = u"Toutes les opérations à fusionner doivent concerner le même partenaire !"
                result['error'] = True
                return result

            if pickings.filtered(lambda p: p.state == 'done'):
                result['info_txt'] = u"Vous ne pouvez pas fusionner d'opérations déjà réalisées !"
                result['error'] = True
                return result

            if pickings.filtered(lambda p: p.state == 'cancel'):
                result['info_txt'] = u"Vous ne pouvez pas fusionner d'opérations annulées !"
                result['error'] = True
                return result

            result['picking_ids'] = [(6, 0, [pickings.ids])]
            result['info_txt'] = u"Vous allez fusionner les opérations suivantes :\n" + \
                                 u"\n".join(['    - %s' % (name or 'N/E') for name in pickings.mapped('name')])
            result['ok'] = True
            return result

    picking_ids = fields.Many2many(comodel_name='stock.picking', string=u"Opérations à fusionner")
    ok = fields.Boolean()
    error = fields.Boolean()
    info_txt = fields.Text()

    @api.multi
    def action_merge_pickings(self):
        self.ensure_one()

        final_picking = self.picking_ids[0]
        other_pickings = self.picking_ids - final_picking

        if len(self.picking_ids.mapped('of_customer_id')) > 1:
            final_picking.of_customer_id = False

        for other_picking in other_pickings:
            for move in other_picking.move_lines:
                move.picking_id = final_picking
            for pack_operation in other_picking.pack_operation_ids:
                pack_operation.picking_id = final_picking
            if other_picking.origin:
                if final_picking.origin:
                    final_picking.origin += ', ' + other_picking.origin
                else:
                    final_picking.origin = other_picking.origin

        other_pickings.unlink()

        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
        action['res_id'] = final_picking.id

        return action
