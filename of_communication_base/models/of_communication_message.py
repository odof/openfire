# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import ValidationError

DEFAULT_DAYS_DELAY_END_SCHEDULED = 10
DEFAULT_HOURS_DELAY_BEFORE_END_SCHEDULED = 1
DEFAULT_MAX_CHARACTERS = 280


class OfCommunication(models.Model):
    """
    Model representing a Communication Message in OpenFire.
    """

    _name = 'of.communication'
    _inherit = ['mail.thread', 'of.form.readonly']
    _description = "Message"
    _order = 'date desc'

    name = fields.Text(string="Title", required=True, help="Title of the message")
    summary = fields.Text(
        required=True,
        tracking=True,
        help="Content of the notification. The maximum number of characters is 280.\n"
        "This field will be visible on the notification",
    )
    message = fields.Html(help="Content of the message")
    message_type = fields.Selection(
        string="Type",
        selection=[
            ('informative_message', "Informative Message"),
            ('patch_note', "Patch Note"),
            ('non-critical_alert_message', "Non-Critical Alert Message"),
            ('critical_alert_message', "Critical Alert Message"),
        ],
        required=True,
        tracking=True,
        help="Type of the message."
        "Depending on its type, the notification will have a color which will define its urgency:\n"
        "  * Informative Message in blue\n"
        "  * Patch Note in blue\n"
        "  * Non-Critical Alert Message in orange\n"
        "  * Critical Alert Message in red",
    )
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('published', "Published"),
            ('in_edition', "In edition"),
            ('canceled', "Canceled"),
        ],
        required=True,
        default='draft',
        tracking=True,
        help="State of the message",
    )
    message_class_style = fields.Selection(
        selection=[
            ('info', "Info"),
            ('warning', "Warning"),
            ('danger', "Danger"),
        ],
        compute='_compute_style_of_message',
        store=True,
    )
    message_style = fields.Selection(
        selection=[
            ('banner', "Banner"),
            ('pop-up', "Pop-up"),
        ],
        compute='_compute_style_of_message',
        required=True,
        store=True,
        help="Style of the message.\n"
        "Depending on its style, the notification will have a different form:\n"
        "  * Banner: a banner will appear at the top of the customer page\n"
        "  * Pop-up: a pop-up will appear at the top right of the customer page",
    )
    date = fields.Date(readonly=True, default=fields.Date.today, required=True, copy=False, help="Creation date")
    start_scheduled_publication = fields.Datetime(
        string="Start of Scheduled Publication",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        help="The message's display date and time.",
    )
    end_scheduled_publication = fields.Datetime(
        string="End of Scheduled Publication",
        tracking=True,
        compute='_compute_end_scheduled_publication',
        store=True,
        help="The notification's removed date and time.",
    )
    end_message = fields.Datetime(
        string="End of life of the Message",
        tracking=True,
        help="The message's removed date and time.",
    )
    is_sending_notification = fields.Boolean(
        string="Resend Message",
        tracking=True,
        default=True,
        help="If enable then a notification will be sent",
    )
    is_message_edited = fields.Boolean(default=False)
    is_preview = fields.Boolean(default=False)
    is_internal = fields.Boolean()
    active = fields.Boolean(default=True)

    def action_button_publish(self):
        """
        Function to publish the message if its state is 'draft'.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError(_("You can only publish a message in 'Draft' or 'In Edition' state."))
            record.state = 'published'
            record.is_preview = False

    def action_all_publish(self):
        """
        Function to publish all messages whose state is 'draft'.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if record.state in ['draft', 'in_edition']:
                record.state = 'published'
                record.is_preview = False

    def action_button_edit(self):
        """
        Function to edit a message whose state is 'Published'.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if record.state not in ['published', 'canceled']:
                raise exceptions.UserError(_("You can only edit a message in 'Published' or 'Canceled' state."))
            record.update(
                {
                    'state': 'in_edition',
                    'is_message_edited': True,
                }
            )

    def action_button_publish_edit(self):
        """
        Function to publish a message whose state is 'in_edition'.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if record.state != 'in_edition':
                raise exceptions.UserError(_("You can only publish a message in 'Draft' or 'In Edition' state."))
            record.state = 'published'
            record.is_preview = False

    def action_button_cancel(self):
        """
        Function to cancel a message whose state is 'draft'.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if record.state not in ['draft', 'in_edition']:
                raise exceptions.UserError(_("You can only cancel a message in 'Draft' or 'In Edition' state."))
            record.state = 'canceled'

    def unlink(self):
        """
        Function to delete a message whose state is 'canceled'.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if not self.env.context.get('of_force_message_delete') and record.state != 'canceled':
                raise exceptions.UserError(_("You can only delete messages that are in 'Canceled' state."))
        return super().unlink()

    def action_button_preview(self):
        """
        Function to see a preview of the notification.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if record.state not in ['draft', 'in_edition']:
                raise exceptions.UserError(_("You can only preview a notification in 'Draft' or 'In Edition' state."))
            record.is_preview = True
            record._dispatch_preview_notification()

    def _dispatch_preview_notification(self):
        """
        Retrieves all information from a message.
        Then for each message it will create a preview of the notification.

        Args:
            None
        Returns:
            None
        """
        users = self.env['res.users'].search([])  # TODO: Filter users ?

        for message in self:
            message_content, message_style = message._get_message_content()
            message_type = message.message_type
            message_type_label = dict(message._fields['message_type'].selection).get(message_type)
            users_to_notify = users.filtered(lambda u: u.id == self.env.user.id)
            for user in users_to_notify:
                if user.has_group('base.group_user'):
                    self.env['bus.bus']._sendone(
                        user.partner_id,
                        message_style,
                        {
                            'button_see_more_label': _("See More"),
                            'button_see_later_label': _("See Later"),
                            'message': message_content,
                            'type': message.message_class_style,
                            'style': message.message_style,
                            'message_is_html': True,
                            'message_id': message.id,
                            'is_preview': message.is_preview,
                            'title': message.name,
                            'date': message.date,
                            'end_message': message.end_message,
                            'summary': message.summary,
                            'message_content': message.message,
                            'message_type': message_type_label,
                        },
                    )

    def _resend_unread_notifications(self):
        """
        Retrieves all information from a message and message logs.
        Only takes unread notifications.
        And returns the notifications which validate all the conditions.

        Args:
            None
        Returns:
            None
        """
        notification_log_obj = self.env['of.communication.notification.log']
        unread_logs = notification_log_obj.search(
            [
                ('is_marked_as_read', '=', False),
            ]
        )

        now = fields.Datetime.now()
        messages_to_notify = {}

        for log in unread_logs:
            message = log.message_id
            if log.is_recall_activate:
                if now >= log.recall_date or (
                    log.message_id.end_scheduled_publication
                    and (log.message_id.end_scheduled_publication - now)
                    <= timedelta(minutes=DEFAULT_HOURS_DELAY_BEFORE_END_SCHEDULED)
                ):
                    if message in messages_to_notify:
                        messages_to_notify[message].append(log.user_id)
                    else:
                        messages_to_notify[message] = [log.user_id]
            else:
                if message in messages_to_notify:
                    messages_to_notify[message].append(log.user_id)
                else:
                    messages_to_notify[message] = [log.user_id]

        for message, users in messages_to_notify.items():
            message_content, message_style = message._get_message_content()
            message_type = message.message_type
            message_type_label = dict(message._fields['message_type'].selection).get(message_type)
            for user in users:
                if user.has_group('base.group_user'):
                    if message.is_sending_notification:
                        self.env['bus.bus']._sendone(
                            user.partner_id,
                            message_style,
                            {
                                'button_see_more_label': _("See More"),
                                'button_see_later_label': _("See Later"),
                                'message': message_content,
                                'type': message.message_class_style,
                                'style': message.message_style,
                                'message_is_html': True,
                                'message_id': message.id,
                                'is_preview': message.is_preview,
                                'title': message.name,
                                'date': message.date,
                                'end_message': message.end_message,
                                'summary': message.summary,
                                'message_content': message.message,
                                'message_type': message_type_label,
                            },
                        )

    def _dispatch_notification(self):
        """
        Fetches created messages and retrieves all users and all notification logs.
        Then for each message, it creates a link to view it and gives a type (danger, warning, info),
        based on the type (critical_alert_message, non-critical_alert_message, other),
        then for each user it creates a notification from a java script file and creates a notification log object.

        Args:
            None
        Returns:
            None
        """
        users = self.env['res.users'].search([])  # TODO: Filter users ?
        notification_log_obj = self.env['of.communication.notification.log']

        for message in self:
            message_content, message_style = message._get_message_content()
            message_type = message.message_type
            message_type_label = dict(message._fields['message_type'].selection).get(message_type)
            users_to_notify = users.filtered(lambda u: u.id != message.create_uid.id)
            for user in users_to_notify:
                if user.has_group('base.group_user'):
                    if message.is_sending_notification:
                        notification_exists = (
                            notification_log_obj.search_count(
                                [
                                    ('user_id', '=', user.id),
                                    ('message_id', '=', message.id),
                                ]
                            )
                            > 0
                        )
                        if not notification_exists:
                            notification_log_obj.create(
                                {
                                    'user_id': user.id,
                                    'message_id': message.id,
                                    'is_marked_as_read': False,
                                }
                            )
                        else:
                            notification_log_obj.write(
                                {
                                    'is_marked_as_read': False,
                                }
                            )

                        self.env['bus.bus']._sendone(
                            user.partner_id,
                            message_style,
                            {
                                'button_see_more_label': _("See More"),
                                'button_see_later_label': _("See Later"),
                                'message': message_content,
                                'type': message.message_class_style,
                                'style': message.message_style,
                                'message_is_html': True,
                                'message_id': message.id,
                                'is_preview': message.is_preview,
                                'title': message.name,
                                'date': message.date,
                                'end_message': message.end_message,
                                'summary': message.summary,
                                'message_content': message.message,
                                'message_type': message_type_label,
                            },
                        )

    def _delete_notification(self):
        """
        Deletes notifications and their logs for the given messages.

        Args:
            None
        Returns:
            None
        """
        notification_log_obj = self.env['of.communication.notification.log']

        for message in self:
            notification_logs = notification_log_obj.search([('message_id', '=', message.id)])

            if notification_logs:
                notification_logs.unlink()

            users = self.env['res.users'].search([('active', '=', True)])
            for user in users:
                if user.has_group('base.group_user'):
                    self.env['bus.bus']._sendone(
                        user.partner_id,
                        'of_notification_removal',
                        {
                            'notification_type': message.message_style,
                            'message_id': message.id,
                        },
                    )

    def _get_message_content(self):
        """
        Retrieves the message content.

        Args:
            None
        Returns:
            str: The message content.
        """
        self.ensure_one()

        message_style = 'of_banner_notification'
        if self.message_style != 'banner':
            message_style = 'of_popup_notification'

        message_content = f"{self.summary}"

        return message_content, message_style

    @api.depends('message_type')
    def _compute_style_of_message(self):
        """
        Function to calculate the message class style based on its type.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if record.message_type == 'critical_alert_message':
                record.message_class_style = 'danger'
                record.message_style = 'banner'
            elif record.message_type == 'non-critical_alert_message':
                record.message_class_style = 'warning'
                record.message_style = 'banner'
            else:
                record.message_class_style = 'info'
                record.message_style = 'pop-up'

    @api.depends('start_scheduled_publication')
    def _compute_end_scheduled_publication(self):
        """
        Function to calculate the end of scheduled publication for a message.

        Args:
            None
        Returns:
            None
        """
        icp_obj = self.env['ir.config_parameter'].sudo()
        delay = int(icp_obj.get_param('of_communication.delay_end_scheduled', DEFAULT_DAYS_DELAY_END_SCHEDULED))
        for message_end_scheduled in self:
            message_end_scheduled.end_scheduled_publication = (
                message_end_scheduled.start_scheduled_publication + timedelta(days=delay)
            )

    @api.constrains('summary')
    def _check_char_max_summary(self):
        """
        Function to check that the summary does not exceed 280 characters.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            if len(record.summary) > DEFAULT_MAX_CHARACTERS:
                raise ValidationError(
                    _("The summary cannot contain more than {} characters.").format(DEFAULT_MAX_CHARACTERS)
                )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to trigger internal notifications when a message is published.

        Args:
            vals_liste (list): The list of dictionaries containing values to create the records with.

        Returns:
            record: The created records.
        """
        records = super(OfCommunication, self).create(vals_list)

        for record, vals in zip(records, vals_list):
            if 'state' in vals and vals['state'] == 'published' and 'is_internal' in vals and vals['is_internal']:
                record._dispatch_notification()

        return record

    def write(self, vals):
        """
        Override the write method to trigger internal notifications when a message's state changes to 'published'.
        Override the write method to trigger internal notifications to be suppressed when a post's
        status changes to 'in_edition'.

        Args:
            vals (dict): The values to write to the record.
        Returns:
            bool: True if the write operation was successful, False otherwise.
        """
        res = super(OfCommunication, self).write(vals)
        if 'state' in vals:
            if vals['state'] == 'published':
                self._dispatch_notification()
            elif vals['state'] == 'in_edition':
                self._delete_notification()
        return res

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        if view_type == 'form':
            self = self.with_context(form_readonly="['|', ('state', '=', 'published'), ('state', '=', 'canceled')]")
        return super()._get_view(view_id=view_id, view_type=view_type, **options)

    @api.model
    def _cron_communication_resend_notification(self):
        """
        This method is responsible for performing a task related to notification returns,
        It executes the following steps:

        1. Resend unread notifications.

        Args:
            None
        Returns:
            None
        """
        self._resend_unread_notifications()
