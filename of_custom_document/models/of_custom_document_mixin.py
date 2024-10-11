# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import io

from odoo import api, fields, models

try:
    import pypdftk
except ImportError:
    pypdftk = None


class OFCustomDocumentMixin(models.AbstractModel):
    """Classe abstraite qui permet d'ajouter les documents joints.
    La fonction _allowed_reports doit être surchargée pour ajouter d'autres rapports et être en héritage pour la classe
    sur laquelle on veut ajouter la fonctionnalité.
    """

    _name = "of.custom.document.mixin"
    _description = "Custom document mixin"

    of_custom_document_ids = fields.Many2many(
        comodel_name="of.custom.document", string="Custom documents", help="Documents to include into pdf reports."
    )

    @api.model
    def _allowed_reports(self):
        """
        :return: ['report_name']
        """
        return []

    @api.model
    def is_allowed_report(self, report):
        return report.report_name in self._allowed_reports()

    def join_custom_documents(self, pdf_content, record=None):
        self.ensure_one()
        if not self.of_custom_document_ids:
            return pdf_content
        if self._name != "ir.actions.report":
            record = self
        streams_to_merge = [io.BytesIO(pdf_content)]
        for document in self.of_custom_document_ids:
            if rendered_file := document.render_file(record.ids):
                streams_to_merge.append(io.BytesIO(rendered_file[0]))
        with self.env["ir.actions.report"]._merge_pdfs(streams_to_merge) as pdf_merged_stream:
            pdf_content = pdf_merged_stream.getvalue()
        return pdf_content
