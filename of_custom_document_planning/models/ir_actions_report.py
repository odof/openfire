# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import io

from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _report_intervention_sheet_append(self, record, template, streams_to_merge):
        """Append reports and joined documents to the intervention sheet PDF depending on the template settings.
        :param record: intervention record
        :param template: intervention template
        :param streams_to_merge: list of streams to merge
        """
        if record.of_order_id and template.sheet_order_pdf:
            order_pdf, _type = self._render_qweb_pdf('sale.report_saleorder', res_ids=record.of_order_id.id, data=None)
            streams_to_merge.append(io.BytesIO(order_pdf))

        if record.of_picking_manual_ids and template.sheet_picking_pdf:
            pickings_pdf, _type = self._render_qweb_pdf(
                'stock.report_deliveryslip', res_ids=record.of_picking_manual_ids.ids, data=None
            )
            streams_to_merge.append(io.BytesIO(pickings_pdf))

        if record.of_invoice_ids and template.sheet_invoice_pdf:
            invoices_pdf, _type = self._render_qweb_pdf(
                'account.report_invoice', res_ids=record.of_invoice_ids.ids, data=None
            )
            streams_to_merge.append(io.BytesIO(invoices_pdf))

        for document in template.sheet_custom_document_ids:
            if rendered_file := document.render_file(record.ids):
                streams_to_merge.append(io.BytesIO(rendered_file[0]))

    def _report_intervention_report_append(self, record, template, streams_to_merge):
        """Append reports and joined documents to the intervention report PDF depending on the template settings.
        :param record: intervention record
        :param template: intervention template
        :param streams_to_merge: list of streams to merge"""
        if record.of_order_id and template.report_order_pdf:
            order_pdf, _type = self._render_qweb_pdf('sale.report_saleorder', res_ids=record.of_order_id.id, data=None)
            streams_to_merge.append(io.BytesIO(order_pdf))

        if record.of_picking_manual_ids and template.report_picking_pdf:
            pickings_pdf, _type = self._render_qweb_pdf(
                'stock.report_deliveryslip', res_ids=record.of_picking_manual_ids.ids, data=None
            )
            streams_to_merge.append(io.BytesIO(pickings_pdf))

        if record.of_invoice_ids and template.report_invoice_pdf:
            invoices_pdf, _type = self._render_qweb_pdf(
                'account.report_invoice', res_ids=record.of_invoice_ids.ids, data=None
            )
            streams_to_merge.append(io.BytesIO(invoices_pdf))

        for document in template.report_custom_document_ids:
            if rendered_file := document.render_file(record.ids):
                streams_to_merge.append(io.BytesIO(rendered_file[0]))

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf_content, file_type = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        report = self._get_report(report_ref)

        if report.report_name in [
            'of_planning.report_intervention_sheet',
            'of_planning.report_intervention_report',
        ]:
            default_template = self.env.ref(
                'of_planning.of_planning_default_intervention_template', raise_if_not_found=False
            )
            streams_to_merge = [io.BytesIO(pdf_content)]
            records = self.env[report.model].browse(res_ids)
            for record in records:
                template = record.of_template_id or default_template

                # Intervention sheet
                if report.report_name == 'of_planning.report_intervention_sheet':
                    self._report_intervention_sheet_append(record, template, streams_to_merge)

                # Intervention report
                if report.report_name == 'of_planning.report_intervention_report':
                    self._report_intervention_report_append(record, template, streams_to_merge)

            # Merge PDFs
            with self.env['ir.actions.report']._merge_pdfs(streams_to_merge) as pdf_merged_stream:
                pdf_content = pdf_merged_stream.getvalue()

        return pdf_content, file_type
