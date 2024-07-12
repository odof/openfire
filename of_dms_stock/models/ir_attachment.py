# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IRAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        picking_obj = self.env["stock.picking"]
        attachments = super().create(vals_list)
        attachments_pickings = attachments.filtered(lambda r: r.res_model == "stock.picking")
        for attachment_picking in attachments_pickings:
            picking = picking_obj.browse(attachment_picking.res_id)
            if picking.picking_type_code in ["incoming", "outgoing"]:
                attachment_picking.create_dms_files(picking.partner_id, picking.picking_type_code)
        return attachments
