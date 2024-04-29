# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, exceptions, fields, models
from odoo.exceptions import ValidationError


class OfCommunication(models.Model):
    _name = 'of.communication'
    _inherit = 'mail.thread'
    _description = 'Message object, which contains all the variables'
    _order = 'date desc'

    name = fields.Text(string="Title", required=True, help="Title of message")
    date = fields.Date(
        string="Date", default=fields.Date.today, required=True, copy=False, help="Post publication date"
    )
    type = fields.Selection(
        string="Type",
        selection=[
            ('informative_message', "Informative Message"),
            ('patch_note', "Patch Note"),
            ('non-critical_alert_message', "Non-Critical Alert Message"),
            ('critical_alert_message', "Critical Alert Message"),
        ],
        required=True,
        help="Type of message",
    )
    state = fields.Selection(
        string="State",
        readonly=True,
        selection=[
            ('draft', "Draft"),
            ('published', "Published"),
            ('edit', "Edit"),
            ('canceled', "Canceled"),
        ],
        required=True,
        default="draft",
        help="State of message",
    )
    active = fields.Boolean(string="Archived", default=True)
    start_scheduled_publication = fields.Datetime(
        string="Start of Scheduled Publication",
        readonly=False,
        required=True,
        help="The message's display date and time.",
    )
    end_scheduled_publication = fields.Datetime(
        string="End of Scheduled Publication",
        readonly=False,
        help="The message's removed date and time. If not set, it stays visible until replaced by a new message.",
    )
    summary = fields.Text(
        string="Summary",
        default="",
        required=True,
        help="Content of the message notification. The maximum number of characters is 280",
    )
    message = fields.Html(string="Message", help="Content of the message")

    def of_action_publish(self):
        for record in self:
            if record.state in ['published', 'edit', 'canceled']:
                raise exceptions.UserError("You can only publish message in 'Draft' state.")
            record.state = 'published'

    def of_action_all_publish(self):
        for record in self:
            if record.state in ['draft', 'edit']:
                record.state = 'published'

    def of_action_edit(self):
        for record in self:
            if record.state not in ['published']:
                raise exceptions.UserError("You can only edit message in 'Published' state.")
            record.state = 'edit'

    def of_action_publish_edit(self):
        for record in self:
            if record.state in ['published', 'canceled']:
                raise exceptions.UserError("You can only publish message in 'Edit' state.")
            record.state = 'published'

    def of_action_cancel(self):
        for record in self:
            if record.state in ['published']:
                raise exceptions.UserError('You can only cancel message in \'Draft\' state.')
            record.state = 'canceled'

    @api.constrains('summary')
    def _check_char_max_summary(self):
        for record in self:
            if len(record.summary) > 280:
                raise ValidationError('You cannot have more than 280 characters in the summary')
