# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import io

from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf_content, file_type = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        report = self._get_report(report_ref)
        if report.report_name == 'sale.report_saleorder' and self.user_has_groups(
            'of_sale_report_setting.group_of_sale_report_print_attachment'
        ):
            # Ajout des PJ des articles à la fin du rapport Devis/Commande
            if res_ids and (isinstance(res_ids, int) or len(res_ids) == 1):
                record = self.env[report.model].browse(res_ids)
                product_attachments = record.order_line.mapped('of_product_attachment_ids')

                streams_to_merge = [io.BytesIO(pdf_content)]
                for attach in product_attachments:
                    rendered_file = base64.b64decode(attach.datas)
                    if not rendered_file:
                        continue
                    streams_to_merge.append(io.BytesIO(rendered_file))
                with self.env['ir.actions.report']._merge_pdfs(streams_to_merge) as pdf_merged_stream:
                    pdf_content = pdf_merged_stream.getvalue()

        return pdf_content, file_type
