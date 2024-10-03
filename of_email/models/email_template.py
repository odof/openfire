# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    of_reply_to = fields.Char(
        string="Force Reply-To",
        help='This field allows you to force the "Reply-To" field of the email in the Mail Composer. Warning: '
        'This field is mutually exclusive with the "Reply-To" field, which will be emptied if this field is set.'
        "This field is not used in mass mailing.",
    )

    @api.onchange("of_reply_to")
    def _onchange_of_reply_to(self):
        if self.of_reply_to and self.reply_to:
            result = {
                "warning": {
                    "title": _("Warning!"),
                    "message": _(
                        'The "Force Reply-To" field will be used instead of the "Reply-To" field.'
                        'Those fields are mutually exclusive. The field "Reply-To" (%(reply_to)s) was emptied.',
                        reply_to=self.reply_to,
                    ),
                }
            }
            self.reply_to = False
            return result

    @api.onchange("reply_to")
    def _onchange_reply_to(self):
        if self.reply_to and self.of_reply_to:
            result = {
                "warning": {
                    "title": _("Warning!"),
                    "message": _(
                        'The "Reply-To" field will be used instead of the "Force Reply-To" field.'
                        "Those fields are mutually exclusive."
                        'The field "Force Reply-To" (%(of_reply_to)s) was emptied.',
                        of_reply_to=self.of_reply_to,
                    ),
                }
            }
            self.of_reply_to = False
            return result
