# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        move_obj = self.env["account.move"]
        attachments = super().create(vals_list)
        attachments_invoices = attachments.filtered(lambda r: r.res_model == "account.move")
        for attachment_invoice in attachments_invoices:
            invoice = move_obj.browse(attachment_invoice.res_id)
            if invoice.move_type in ["in_invoice", "in_refund"]:
                attachment_invoice.create_dms_files(invoice.partner_id, "IN")
            if invoice.move_type in ["out_invoice", "out_refund"]:
                attachment_invoice.create_dms_files(invoice.partner_id, "OUT")
        return attachments
