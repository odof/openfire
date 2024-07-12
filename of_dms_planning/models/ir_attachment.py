# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        order_obj = self.env["calendar.event"]
        attachments = super().create(vals_list)
        attachments_interventions = attachments.filtered(lambda r: r.res_model == "calendar.event")
        for attachment_intervention in attachments_interventions:
            intervention = order_obj.browse(attachment_intervention.res_id)
            attachment_intervention.create_dms_files(intervention.of_partner_id)
        return attachments
