# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    def create_dms_files(self, partner, code=False):
        """Create DMS file for attachment"""
        directory_obj = self.env["dms.directory"].with_context({"active_test": False})
        file_obj = self.env["dms.file"]
        for attachment in self.filtered(lambda r: r.res_model):
            if attachment.res_model == "res.partner":
                directory = partner.of_dms_directory_id
            else:
                directory = directory_obj.search(
                    [
                        ("parent_id", "=", partner.of_dms_directory_id.id),
                        ("res_model", "=", attachment.res_model),
                        ("of_code", "=", code),
                    ],
                    limit=1,
                )
            if directory:
                if not directory.active:
                    directory.active = True

                dms_file = file_obj.search(
                    [
                        ("attachment_id", "=", attachment.id),
                        ("directory_id", "=", directory.id),
                    ]
                )
                if not dms_file:
                    file_obj.create(
                        {
                            "name": attachment.name,
                            "directory_id": directory.id,
                            "attachment_id": attachment.id,
                            "res_model": attachment.res_model,
                            "res_id": attachment.res_id,
                        }
                    )

    @api.model_create_multi
    def create(self, vals_list):
        partner_obj = self.env["res.partner"]
        attachments = super().create(vals_list)
        attachments_partners = attachments.filtered(lambda r: r.res_model == "res.partner")
        for attachment_partner in attachments_partners:
            attachment_partner.create_dms_files(partner_obj.browse(attachment_partner.res_id))
        return attachments
