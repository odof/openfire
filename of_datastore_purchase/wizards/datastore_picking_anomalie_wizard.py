# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFDatastorePickingAnomalieWizard(models.TransientModel):
    _name = 'of.datastore.picking.anomalie.wizard'

    picking_id = fields.Many2one(comodel_name='stock.picking', string=u"Bon de réception")
    text = fields.Text(string="Message")

    @api.multi
    def button_send(self):
        datastore_obj = self.env['of.datastore.purchase']
        datastore = datastore_obj.search([('partner_id', '=', self.picking_id.partner_id.id)])
        if datastore:
            client = datastore.of_datastore_connect()
            if not isinstance(client, basestring):
                ds_picking_obj = datastore.of_datastore_get_model(client, 'stock.picking')
                datastore.of_datastore_func(ds_picking_obj, 'message_post_xmlrpc', [self.picking_id.of_datastore_id],
                                            [('body', self.text), ('content_subtype', "plaintext")])
                datastore.of_datastore_func(ds_picking_obj, 'write', [self.picking_id.of_datastore_id],
                                            [('vals', {'of_datastore_anomalie': True})])
                self.picking_id.write({'of_datastore_anomalie': True})
                self.picking_id.message_post(body=self.text, content_subtype="plaintext")
