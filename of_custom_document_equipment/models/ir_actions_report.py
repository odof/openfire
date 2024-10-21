# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import io

from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _report_equipment_report_append(self, record, template, streams_to_merge):
        """Append reports and joined documents to the equipment link report PDF depending on the template settings.

        Args:
            record (of.calendar.event.equipment.link): equipment link record
            template (of.equipment.intervention.report.template): equipment report template
            streams_to_merge (list): list of streams to merge
        """

        for document in template.report_custom_document_ids:
            if rendered_file := document.render_file(record.ids):
                streams_to_merge.append(io.BytesIO(rendered_file[0]))

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf_content, file_type = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        report = self._get_report(report_ref)

        if report.report_name in ["of_equipment.report_equipment_link_report"]:
            streams_to_merge = [io.BytesIO(pdf_content)]
            records = self.env[report.model].browse(res_ids)
            for record in records:
                # If there is no equipment report template, we use the default one
                # stored on the calendar event template if exists
                if template := (
                    record.equipment_report_tmpl_id or record.event_id.of_default_equipment_report_tmpl_id or False
                ):
                    self._report_equipment_report_append(record, template, streams_to_merge)

            # Merge PDFs
            with self.env["ir.actions.report"]._merge_pdfs(streams_to_merge) as pdf_merged_stream:
                pdf_content = pdf_merged_stream.getvalue()

        return pdf_content, file_type
