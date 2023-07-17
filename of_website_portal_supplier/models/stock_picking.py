# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, api, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_shipment_date = fields.Datetime(string=u"Date d’expédition réelle", copy=False, track_visibility='onchange')
    of_shipped_by_supplier = fields.Boolean(string=u"Expédié par le fournisseur", copy=False)

    def _prepare_division_values(self):
        """
        On prépare les valeurs en les scindant dans deux listes.
        Une pour le BR qui va être divisé et l'autre pour le nouveau BR
        """
        self.ensure_one()
        vals = {
            'old_picking': [],
            'new_picking': [],
        }
        for line in self.pack_operation_product_ids:
            if line.of_shipped_qty:
                lots = line.pack_lot_ids.filtered(lambda l: l.of_shipped_qty)
                lots_data = [
                    {
                        'lot_id': lot.lot_id.id,
                        'qty_todo': lot.qty_todo,
                        'of_shipped_qty': lot.of_shipped_qty,
                        'of_expected_shipment_date': lot.of_expected_shipment_date,
                    }
                    for lot in lots
                ]
                vals['old_picking'].append({
                    'id': line.id,
                    'product_id': line.product_id,
                    'product_qty': line.of_shipped_qty,
                    'of_shipped_qty': line.of_shipped_qty,
                    'of_expected_shipment_date': line.of_expected_shipment_date,
                    'pack_lot_ids': lots_data,
                })
            if line.of_shipped_qty < line.product_qty:
                lots = line.pack_lot_ids.filtered(lambda l: l.of_shipped_qty < l.qty_todo)
                lots_data = [
                    {
                        'lot_id': lot.lot_id.id,
                        'qty_todo': lot.qty_todo,
                        'of_shipped_qty': lot.of_shipped_qty,
                        'of_expected_shipment_date': lot.of_expected_shipment_date,
                    }
                    for lot in lots
                ]
                vals['new_picking'].append({
                    'id': line.id,
                    'product_id': line.product_id,
                    'product_qty': line.product_qty - line.of_shipped_qty,
                    'of_shipped_qty': 0,
                    'of_expected_shipment_date': line.of_expected_shipment_date,
                    'pack_lot_ids': lots_data,
                })
        return vals

    @api.model
    def cron_ship_picking_from_suppliers(self):
        """
        On traite les BR à expédier. Si besoin, on les divise en les annulant leurs reservations et
        en recréant les opérations/lots derrière
        """
        delivery_division_obj = self.env['of.delivery.division.wizard']
        operation_lot_obj = self.env['stock.pack.operation.lot']
        delay = self.env['ir.values'].sudo().get_default(
            'website.config.settings', 'of_picking_rollback_delay_minutes_supplier')

        time_for_domain = fields.Datetime.to_string(datetime.now() - relativedelta(minutes=delay))
        domain = [('state', 'not in', ['done', 'cancel']), ('of_shipment_date', '<=', time_for_domain),
                  ('of_shipped_by_supplier', '=', False)]
        pickings_done = self

        # Les BR à expédier
        pickings_to_ship = self.search(domain)
        for picking in pickings_to_ship:
            # On regarde si il y a besoin de le diviser
            need_division = any(
                po_line.product_qty != po_line.of_shipped_qty
                for po_line in picking.pack_operation_product_ids
            )
            if not need_division:
                pickings_done += picking
                continue

            operations_data = picking._prepare_division_values()
            move_to_unreserve = picking.move_lines.filtered(
                lambda ml: all(qty != 0 for qty in ml.mapped(
                    'linked_move_operation_ids.operation_id.of_shipped_qty')))
            try:
                # On annule les réservations
                move_to_unreserve.action_reset()
                action = picking.action_delivery_division()
                if action and action.get('res_id'):
                    wizard = delivery_division_obj.browse(action['res_id'])
                    for line in wizard.line_ids:
                        for operation in operations_data['new_picking']:
                            if operation['product_id'] == line.product_id:
                                line.qty_to_divide = operation['product_qty']

                    # On divise
                    new_action = wizard.action_delivery_division()

                    if new_action:
                        # On recrée les opérations et lots
                        picking.action_assign()
                        for line in picking.pack_operation_product_ids:
                            for operation in operations_data['old_picking']:
                                if operation['product_id'] == line.product_id:
                                    line.write({
                                        'of_shipped_qty': operation['of_shipped_qty'],
                                        'of_expected_shipment_date': operation['of_expected_shipment_date'],
                                    })
                                    for lot in operation['pack_lot_ids']:
                                        lot_data = lot
                                        lot_data['operation_id'] = line.id
                                        operation_lot_obj.create(lot_data)

                        new_picking = self.env['stock.picking'].browse(new_action['res_id'])
                        new_picking.action_assign()
                        for line in new_picking.pack_operation_product_ids:
                            for operation in operations_data['new_picking']:
                                if operation['product_id'] == line.product_id:
                                    line.write({
                                        'of_shipped_qty': operation['of_shipped_qty'],
                                        'of_expected_shipment_date': operation['of_expected_shipment_date'],
                                    })
                                    for lot in operation['pack_lot_ids']:
                                        lot_data = lot
                                        lot_data['operation_id'] = line.id
                                        operation_lot_obj.create(lot_data)
                pickings_done += picking
            except Exception:
                continue
        if pickings_done:
            # On marque le BR comme expédié
            pickings_done.write({'of_shipped_by_supplier': True})
