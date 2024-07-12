# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """
        Pour un rapport de facture, on supprime le fichier DMS virtuel qui est remplacé par le pdf qui va être rendu.
        """
        pdf_content, file_type = super()._render_qweb_pdf(report_ref, res_ids, data)
        if report_ref == "account.report_invoice_with_payments":
            virtual_report = self.env["of.dms.virtual_file_report"].search(
                [
                    ("company_id", "=", self.env.user.company_id.id),
                    ("model_name", "=", "account.move"),
                ],
                limit=1,
            )
            if virtual_report:
                records = self.env["account.move"].browse(res_ids).filtered(lambda r: r.state not in ["draft"])
                files = self.env["dms.file"].search(
                    [
                        ("of_type", "=", "virtual"),
                        ("of_virtual_res_model.model", "=", "account.move"),
                        ("of_virtual_res_id", "in", records.ids),
                        ("of_content_url", "ilike", f"/report/html/{report_ref}"),
                    ]
                )
                files.unlink()

        return pdf_content, file_type
