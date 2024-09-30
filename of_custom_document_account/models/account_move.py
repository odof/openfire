# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "of.custom.document.mixin"]

    of_custom_document_ids = fields.Many2many(
        comodel_name="of.custom.document",
        string="Custom documents",
        help="Documents to include into pdf reports.",
    )

    @api.model
    def _allowed_reports(self):
        return ["account.report_invoice", "account.report_invoice_with_payments", "account.report_original_vendor_bill"]
