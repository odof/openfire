# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_send_sms(self):
        return self.env["of.sms"].action_send_sms(self.id, "sale.order", self.partner_id)
