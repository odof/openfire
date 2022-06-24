# -*- coding: utf-8 -*-

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        # Check if attachments are related to published DMS files
        for attachment in self:
            published_dms_file = self.env['muk_dms.file'].search(
                [('of_attachment_id', '=', attachment.id), ('of_website_published', '=', True)])
            if not published_dms_file:
                return super(IrAttachment, self).read(fields, load=load)
        return super(IrAttachment, self.sudo()).read(fields, load=load)
