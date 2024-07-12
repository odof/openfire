# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        order_obj = self.env["sale.order"]
        attachments = super().create(vals_list)
        attachments_sales = attachments.filtered(lambda r: r.res_model == "sale.order")
        for attachment_sale in attachments_sales:
            sale = order_obj.browse(attachment_sale.res_id)
            attachment_sale.create_dms_files(sale.partner_id)
        return attachments
