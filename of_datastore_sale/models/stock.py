# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def message_post_xmlrpc(self, body='', subject=None, message_type='notification', subtype=None,
                            parent_id=False, attachments=None, content_subtype='html', **kwargs):
        self.message_post(body=body, subject=subject, message_type=message_type, subtype=subtype, parent_id=parent_id,
                          attachments=attachments, content_subtype=content_subtype, **kwargs)
        return True

