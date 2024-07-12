# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        request_obj = self.env["of.service.request"]
        attachments = super().create(vals_list)
        attachments_services = attachments.filtered(lambda r: r.res_model == "of.service.request")
        for attachment_service in attachments_services:
            service = request_obj.browse(attachment_service.res_id)
            attachment_service.create_dms_files(service.partner_id)
        return attachments
