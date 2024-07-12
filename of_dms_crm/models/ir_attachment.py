# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        order_obj = self.env["crm.lead"]
        attachments = super().create(vals_list)
        attachments_leads = attachments.filtered(lambda r: r.res_model == "crm.lead")
        for attachment_lead in attachments_leads:
            lead = order_obj.browse(attachment_lead.res_id)
            attachment_lead.create_dms_files(lead.partner_id)
        return attachments
