# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import models, fields, api


class OFReportFileLine(models.Model):
    _inherit = 'of.report.file.line'

    type = fields.Selection(selection_add=[('ged', "Document GED")])
    document_type_id = fields.Many2one(comodel_name='of.document.type', string=u"Type de document")

    @api.onchange('type', 'expr_model')
    def _onchange_type(self):
        res = super(OFReportFileLine, self)._onchange_type()
        self.document_type_id = False
        return res

    @api.multi
    def get_doc_data(self, model_name, record_ids):
        result = super(OFReportFileLine, self).get_doc_data(model_name, record_ids)
        if self.type == 'ged' and self.document_type_id:
            files = self.env['muk_dms.file'].search(
                [('of_related_model', '=', model_name),
                 ('of_related_id', 'in', record_ids),
                 ('of_document_type_id', '=', self.document_type_id.id),
                 ('mimetype', '=', 'application/pdf')])
            final_result = []
            for file in files:
                for i in range(self.copy_nb):
                    final_result.append(base64.b64decode(file.content))
            return final_result
        return result
