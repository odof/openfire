# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SmsSms(models.Model):
    _inherit = "sms.sms"

    state = fields.Selection(selection_add=[("to_send", "To Send")], ondelete={"to_send": "cascade"})
    of_sender_id = fields.Many2one(comodel_name="of.sms.sender", string="Sender")
    of_date_to_send = fields.Date(string="Date to send")
    of_is_commercial = fields.Boolean(string="Is commercial")

    @api.model
    def cron_sms_send_delayed(self):
        """Send SMS that are delayed"""
        sms_ids = self.search([("state", "=", "to_send"), ("of_date_to_send", "=", fields.Date.today())])
        sms_ids.state = "outgoing"
