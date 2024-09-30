# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_send_sms(self):
        return self.env["of.sms"].action_send_sms(self.id, "account.move", self.partner_id)
