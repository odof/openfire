# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFCustomDocumentField(models.Model):
    _name = 'of.custom.document.field'
    _description = "PDF field"
    _inherit = 'mail.render.mixin'

    name = fields.Char(string="PDF field name", required=True, readonly=True)
    value = fields.Char(string="PDF field value")
    document_id = fields.Many2one(comodel_name='of.custom.document', string="Document")
    to_export = fields.Boolean(string="Export", default=True)
    to_import = fields.Boolean(string="Import")
    lang = fields.Char(related='document_id.lang')

    @api.depends('document_id', 'document_id.render_model')
    def _compute_render_model(self):
        for doc_field in self:
            doc_field.render_model = doc_field.document_id.render_model
