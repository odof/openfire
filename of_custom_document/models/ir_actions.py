# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _name = 'ir.actions.report'
    _inherit = ['ir.actions.report', 'of.custom.document.mixin']

    of_custom_document_ids = fields.Many2many(comodel_name='of.custom.document', domain="[('model', '=', model)]")

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report_sudo = self._get_report(report_ref)
        # Cas des rapports personnalisés à partir d'un fichier (pdf, formulaire pdf ou image)
        if report_sudo.report_name.startswith('of_custom_document.'):
            document = self.env['of.custom.document'].browse(int(report_sudo.report_name.split('.')[1]))
            if document.file:
                return self._render_pdf_form(report_ref, res_ids=res_ids, data=data)

        pdf_content, file_type = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        # Ajout de documents personnalisés à la fin d'un rapport pdf
        if res_ids and (isinstance(res_ids, int) or len(res_ids) == 1):
            record = self.env[report_sudo.model].browse(res_ids)
            # On prend en priorité les documents
            if report_sudo.of_custom_document_ids:
                pdf_content = report_sudo.join_custom_documents(pdf_content, record)
            if hasattr(record, 'join_custom_documents') and record.is_allowed_report(report_sudo):
                pdf_content = record.join_custom_documents(pdf_content)
        return pdf_content, file_type

    def _render_template(self, template, values=None):
        if template.startswith('of_custom_document.'):
            document = self.env['of.custom.document'].browse(int(template.split('.')[1]))
            if values is None:
                values = {}
            values['of_custom_document'] = document
            template = 'of_custom_document.report_of_custom_document'
        return super()._render_template(template, values=values)

    @api.model
    def _render_pdf_form(self, report_ref, res_ids=None, data=None):
        if not data:
            data = {}
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        data.setdefault('report_type', 'pdf')

        # access the report details with sudo() but keep evaluation context as current user
        report_sudo = self._get_report(report_ref)

        doc_model, doc_id = report_sudo.report_name.rsplit('.', 1)
        doc_model = doc_model.replace('_', '.')
        doc_id = int(doc_id)
        doc = self.env[doc_model].browse(doc_id)
        pdf_content = doc.render_file(res_ids)

        if res_ids:
            _logger.info(
                "The PDF report has been generated for model: %s, records %s.", report_sudo.model, str(res_ids)
            )

        return pdf_content, 'pdf'
