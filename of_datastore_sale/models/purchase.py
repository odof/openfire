# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def button_confirm(self):
        datastore_obj = self.env['of.datastore.sale']
        datastore = False
        line_link = {}
        if self.customer_id:
            datastore = datastore_obj.search([('partner_ids', 'in', [self.customer_id.id])])
            if datastore:
                for line in self.mapped('order_line'):
                    datastore_purchase_line_id = line.procurement_ids.mapped('sale_line_id.of_datastore_line_id')
                    if len(datastore_purchase_line_id) == 1 and datastore_purchase_line_id[0] > 0:
                        line_link[line] = datastore_purchase_line_id[0]

        res = super(PurchaseOrder, self).button_confirm()
        if datastore and line_link:
            client = datastore.of_datastore_connect()
            if not isinstance(client, basestring):
                ds_po_line_obj = datastore.of_datastore_get_model(client, 'purchase.order.line')
                for line, datastore_purchase_line_id in line_link.iteritems():
                    moves = line.move_ids.filtered(lambda m: m.state not in ['cancel', 'done'])
                    if not moves:
                        continue
                    last_move = moves[-1]
                    ds_move_id, ds_picking_id = datastore.of_datastore_func(
                        ds_po_line_obj, 'get_datastore_move_id', [datastore_purchase_line_id],
                        [('datastore_move_id', last_move.id), ('datastore_picking_id', last_move.picking_id.id)])
                    if ds_move_id:
                        last_move.write({'of_datastore_move_id': ds_move_id})
                    if ds_picking_id:
                        last_move.picking_id.write({'of_datastore_id': ds_picking_id})
        return res


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    group_of_group_datastore_brand_dropshipping = fields.Boolean(
        string="(OF) Livraison directe", help="Autorise l'utilisation de la livraison directe sur les marques.",
        implied_group='of_datastore_sale.of_group_datastore_brand_dropshipping')
