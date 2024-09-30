# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _search_of_state(self, operator, value):
        messages = self.env["mail.mail"].search([("state", operator, value)]).mapped("mail_message_id")
        return [("id", "in", messages.ids)]

    of_state = fields.Selection(
        selection=[
            ("outgoing", "Outgoing"),
            ("sent", "Sent"),
            ("received", "Received"),
            ("exception", "Delivery Failed"),
            ("cancel", "Cancelled"),
        ],
        string="Status (OF)",
        compute="_compute_of_state",
        search="_search_of_state",
    )
    of_failure_reason = fields.Text(
        string="Failure Reason (OF)",
        compute="_compute_of_state",
        help="Failure reason. This is usually the exception thrown by the email server, "
        "stored to ease the debugging of mailing issues.",
    )

    def _compute_of_state(self):
        mail_obj = self.env["mail.mail"]
        for message in self:
            mail = mail_obj.search([("mail_message_id", "=", message.id)], limit=1)
            if not mail:
                message.of_state = False
                message.of_failure_reason = False
                continue

            message.of_state = mail.state
            message.of_failure_reason = mail.failure_reason

    @api.model
    def _get_default_from(self):
        if not self.env.user.email:
            self.env.user.email = self.env.user._get_default_email()
        return super(MailMessage, self)._get_default_from()
