# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def button_create_procurement(self):
        if any(self.mapped('procurement_id').mapped('sale_line_id').mapped('of_datastore_line_id')):
            return super(StockMove, self.with_context(datastore_dropshipping=True)).button_create_procurement()
        else:
            return super(StockMove, self).button_create_procurement()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_datastore_anomalie = fields.Boolean(string="En anomalie")

    @api.multi
    def write(self, vals):
        return super(StockPicking, self).write(vals)

    @api.multi
    def message_post_xmlrpc(self, body='', subject=None, message_type='notification', subtype=None,
                            parent_id=False, attachments=None, content_subtype='html', **kwargs):
        self.message_post(body=body, subject=subject, message_type=message_type, subtype=subtype, parent_id=parent_id,
                          attachments=attachments, content_subtype=content_subtype, **kwargs)
        return True

