# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import api, fields, models

DEFAULT_HOUR_DELAY_RECALL_NOTIFICATION = 1


class OfCommunicationNotificationLog(models.Model):
    """
    Model representing a Notification Log in OpenFire (Customer database).
    """

    _name = 'of.communication.notification.log'
    _description = 'Notification log'

    user_id = fields.Many2one(comodel_name='res.users', string="User")
    message_id = fields.Many2one(comodel_name='of.communication', string="Message", ondelete="cascade")
    recall_date = fields.Datetime(string="Recall Date", compute='_compute_recall_date', store=True)
    action_type = fields.Selection(selection=[('see', "See"), ('not_see', "Not See")])
    is_marked_as_read = fields.Boolean(default=False)
    is_recall_activate = fields.Boolean(default=False)

    @api.depends('create_date')
    def _compute_recall_date(self):
        """
        Function to calculate date of the automatically recall.

        Args:
            None
        Returns:
            None
        """
        for record in self:
            delay_hours = int(
                self.env['ir.config_parameter']
                .sudo()
                .get_param(
                    'of_communication.of_communication_delay_recall_notification',
                    default=DEFAULT_HOUR_DELAY_RECALL_NOTIFICATION,
                )
            )
            if record.create_date:
                record.recall_date = record.create_date + timedelta(hours=delay_hours)
            else:
                record.recall_date = fields.Datetime.now() + timedelta(hours=delay_hours)

    @api.model
    def mark_message(self, message_id=False, action_type='not_see'):
        """
        Function that allows you to mark a user's notifications as read or activate the recall.

        Args:
            message_id (int): The ID of the message to be marked.
            action_type (str): The type of action ('not_see' or 'see').
        Returns:
            None
        """
        user_id = self.env.user.id

        if log_entry := self.search([('user_id', '=', user_id), ('message_id', '=', message_id)], limit=1):
            if action_type == 'see':
                log_entry.write(
                    {
                        'is_marked_as_read': True,
                        'is_recall_activate': False,
                    }
                )
            elif action_type == 'not_see':
                log_entry.write(
                    {
                        'is_marked_as_read': False,
                        'is_recall_activate': True,
                    }
                )
        else:
            self.create(
                {
                    'user_id': user_id,
                    'message_id': message_id,
                    'action_type': action_type,
                    'is_marked_as_read': False,
                    'is_recall_activate': False,
                }
            )
