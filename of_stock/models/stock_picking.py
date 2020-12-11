# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.addons.stock.models.stock_picking import Picking


@api.multi
def do_new_transfer(self):
    for pick in self:
        if pick.state == 'done':
            raise UserError(_('The pick is already validated'))
        pack_operations_delete = self.env['stock.pack.operation']
        if not pick.move_lines and not pick.pack_operation_ids:
            raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
        # In draft or with no pack operations edited yet, ask if we can just do everything
        if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
            # If no lots when needed, raise error
            picking_type = pick.picking_type_id
            if (picking_type.use_create_lots or picking_type.use_existing_lots):
                for pack in pick.pack_operation_ids:
                    if pack.product_id and pack.product_id.tracking != 'none':
                        raise UserError(
                            _('Some products require lots/serial numbers, so you need to specify those first!'))
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
            # TDE FIXME: a return in a loop, what a good idea. Really.
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        if pick.check_backorder():
            view = self.env.ref('stock.view_backorder_confirmation')
            wiz = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
            # TDE FIXME: same reamrk as above actually
            return {
                'name': _('Create Backorder?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.backorder.confirmation',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        for operation in pick.pack_operation_ids:
            if operation.qty_done < 0:
                raise UserError(_('No negative quantities allowed'))
            if operation.qty_done > 0:
                operation.write({'product_qty': operation.qty_done})
            else:
                pack_operations_delete |= operation
        if pack_operations_delete:
            pack_operations_delete.unlink()

        # OF début modification openfire
        view = self.env.ref('of_stock.view_of_stock_date_confirmation')
        wiz = self.env['of.stock.date.confirmation'].create({'pick_id': pick.id})
        forcer_date_move = self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_move')
        if forcer_date_move:
            return {
                'name': _('Confirmer la date'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.stock.date.confirmation',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        # OF fin modification openfire
        self.do_transfer()


Picking.do_new_transfer = do_new_transfer
