# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        order_obj = self.env["purchase.order"]
        attachments = super().create(vals_list)
        attachments_purchases = attachments.filtered(lambda r: r.res_model == "purchase.order")
        for attachment_purchase in attachments_purchases:
            purchase = order_obj.browse(attachment_purchase.res_id)
            attachment_purchase.create_dms_files(purchase.partner_id)
        return attachments
