# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFAddAttachmentActivity(models.TransientModel):
    _inherit = 'of.add.attachment.activity'

    @api.multi
    def action_validate(self):
        res = super(OFAddAttachmentActivity, self).action_validate()
        if self.activity_id.uploaded_attachment_id and self.activity_id.type_id.of_document_type_id:
            dms_file = self.env['muk_dms.file'].search(
                [('of_attachment_id', '=', self.activity_id.uploaded_attachment_id.id)])
            if dms_file:
                dms_file.of_document_type_id = self.activity_id.type_id.of_document_type_id.id
        return res

