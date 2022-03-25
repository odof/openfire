# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if 'of_datastore_anomalie' in vals and not vals['of_datastore_anomalie']:
            datastore_obj = self.env['of.datastore.purchase']
            for record in self:
                datastore = datastore_obj.search([('partner_id', '=', record.partner_id.id)])
                if datastore and record.of_datastore_id:
                    client = datastore.of_datastore_connect()
                    if not isinstance(client, basestring):
                        ds_picking_obj = datastore.of_datastore_get_model(client, 'stock.picking')
                        datastore.of_datastore_func(
                            ds_picking_obj, 'write', [record.of_datastore_id],
                            [('vals', {'of_datastore_anomalie': False})])
        return res

    @api.multi
    def action_receipt_incident(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': u"Anomalie de réception",
            'res_model': 'of.datastore.picking.anomalie.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref('of_datastore_purchase.of_datastore_picking_anomalie_wizard_view_form').id,
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }
