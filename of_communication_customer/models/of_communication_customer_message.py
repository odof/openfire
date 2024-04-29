# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from xmlrpc import client

from odoo import api, fields, models
from odoo.tools import config


class OfCommunicationCustomer(models.Model):
    """
    Model representing a Communication Message in OpenFire (Customer database).
    """

    _inherit = 'of.communication'
    _description = "Message"

    summary = fields.Text(help="Content of the message notification.")
    message_type = fields.Selection(help="Type of the message.")
    end_scheduled_publication = fields.Datetime(help="The message's removed date and time.")
    active = fields.Boolean(default=True)
    source_message_id = fields.Integer(string="Source Message ID", readonly=True)

    def _create_new_message(self):
        """
        Creates a new message and dispatches a notification if any message is created.
        Method that fetches messages whose state is "published" in the parent database,
        but are not present in the child database.

        It also selects those whose publication date and time are earlier, but the end publication date and time
        has not yet passed, then transfers them to the child database to be created.

        It then sends this message to the notification creation function.

        Args:
            None
        Returns:
            None
        """
        now = fields.Datetime.now()
        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('start_scheduled_publication', '<=', now),
                '|',
                ('end_message', '>=', now),
                ('end_message', '=', False),
                ('is_internal', '=', False),
            ]
        )
        existing_msg_ids = existing_messages.mapped('source_message_id')
        domain = [
            ('id', 'not in', existing_msg_ids),
            ('start_scheduled_publication', '<=', now),
            '|',
            ('end_message', '>=', now),
            ('end_message', '=', False),
            ('state', '=', 'published'),
            ('is_internal', '=', False),
        ]
        created_message = self.env['of.communication'].browse()
        for message in self._fetch_parent_messages(domain):
            created_msg = self.create(
                {
                    'name': message['name'],
                    'date': message['date'],
                    'message_type': message['message_type'],
                    'message_style': message['message_style'],
                    'state': 'published',
                    'start_scheduled_publication': message['start_scheduled_publication'],
                    'end_scheduled_publication': message['end_scheduled_publication'],
                    'end_message': message['end_message'],
                    'summary': message['summary'],
                    'message': message['message'],
                    'source_message_id': message['id'],
                    'is_message_edited': message['is_message_edited'],
                    'is_internal': message['is_internal'],
                }
            )
            created_message |= created_msg
        created_message and created_message._dispatch_notification()

    def _update_edited_message(self):
        """
        Fetches messages whose state is "published" and edited in the parent database, and are present in the
        child database.

        It also selects those whose publication date and time are earlier, but the end publication date and time
        has not yet passed, then modifies them in the child database and sets the edition to "false"
        in the parent database.

        It then sends this updated message to the notification creation function.

        Args:
            None
        Returns:
            None
        """
        now = fields.Datetime.now()
        models, db, uid, password = self._get_connection_to_openFire()
        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('start_scheduled_publication', '<=', now),
                '|',
                ('end_message', '>=', now),
                ('end_message', '=', False),
                ('is_internal', '=', False),
            ]
        )
        existing_msg_ids = existing_messages.mapped('source_message_id')

        messages_to_update = []
        domain = [
            ('id', 'in', existing_msg_ids),
            ('start_scheduled_publication', '<=', now),
            '|',
            ('end_message', '>=', now),
            ('end_message', '=', False),
            ('state', '=', 'published'),
            ('is_message_edited', '=', True),
        ]
        for message in self._fetch_parent_messages(domain):
            if child_message := existing_messages.filtered(lambda r: r.source_message_id == message['id']):
                child_message.write(
                    {
                        'name': message['name'],
                        'message_type': message['message_type'],
                        'message_style': message['message_style'],
                        'start_scheduled_publication': message['start_scheduled_publication'],
                        'end_scheduled_publication': message['end_scheduled_publication'],
                        'end_message': message['end_message'],
                        'summary': message['summary'],
                        'message': message['message'],
                        'is_sending_notification': message['is_sending_notification'],
                    }
                )

                self.env['of.communication.notification.log'].search([('message_id', '=', child_message.id)]).write(
                    {'is_marked_as_read': False}
                )

            messages_to_update.append(message['id'])

        models.execute_kw(
            db,
            uid,
            password,
            'of.communication',
            'write',
            [
                messages_to_update,
                {
                    'is_message_edited': False,
                },
            ],
        )

    def _unlink_in_edition_message(self):
        """
        Fetches messages whose state is "published" and are in edition in the parent database, and are present in the
        child database.

        We don't want to keep messages that are in edition in the parent database in the child database.

        Args:
            None
        Returns:
            None
        """
        now = fields.Datetime.now()
        models, db, uid, password = self._get_connection_to_openFire()
        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('start_scheduled_publication', '<=', now),
                '|',
                ('end_message', '>=', now),
                ('end_message', '=', False),
                ('is_internal', '=', False),
            ]
        )
        existing_msg_ids = existing_messages.mapped('source_message_id')

        parent_messages = models.execute_kw(
            db,
            uid,
            password,
            'of.communication',
            'search_read',
            [
                [
                    ('id', 'in', existing_msg_ids),
                    ('start_scheduled_publication', '<=', now),
                    '|',
                    ('end_message', '>=', now),
                    ('end_message', '=', False),
                    ('is_message_edited', '=', True),
                ]
            ],
            {'fields': []},
        )

        for message in parent_messages:
            child_message = existing_messages.filtered(lambda r: r.source_message_id == message['id'])
            child_message._delete_notification()
            child_message.with_context(of_force_message_delete=True).unlink()

    def _unlink_old_message(self):
        """
        Fetches messages whose state is "published" and are present in the child database, but whose end publication
        date and time have passed.

        Args:
            None
        Returns:
            None
        """
        now = fields.Datetime.now()
        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('end_message', '>=', now),
                ('is_internal', '=', False),
            ]
        )

        for message in existing_messages:
            message._delete_notification()
            message.with_context(of_force_message_delete=True).unlink()

    def _unlink_missing_in_parent(self):
        """
        Deletes messages that are published and present in the child database but not in the parent database.

        Args:
            None
        Returns:
            None
        """
        now = fields.Datetime.now()
        models, db, uid, password = self._get_connection_to_openFire()

        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('start_scheduled_publication', '<=', now),
                ('end_message', '>=', now),
                ('is_internal', '=', False),
            ]
        )
        existing_msg_ids = existing_messages.mapped('source_message_id')

        parent_messages = models.execute_kw(
            db,
            uid,
            password,
            'of.communication',
            'search_read',
            [
                [
                    ('id', 'in', existing_msg_ids),
                    ('start_scheduled_publication', '<=', now),
                    ('end_message', '>=', now),
                ]
            ],
            {'fields': ['id']},
        )
        parent_msg_ids = [msg['id'] for msg in parent_messages]

        missing_in_parent = existing_messages.filtered(lambda r: r.source_message_id not in parent_msg_ids)
        for message in missing_in_parent:
            message._delete_notification()
            message.with_context(of_force_message_delete=True).unlink()

    def _fetch_parent_messages(self, domain):
        """
        Fetches parent messages based on the given domain.

        Args:
            domain (list): A domain to filter the parent messages.
        Returns:
            list: A list of parent messages matching the given domain.
        """
        models, db, uid, password = self._get_connection_to_openFire()
        return models.execute_kw(db, uid, password, 'of.communication', 'search_read', [domain], {'fields': []})

    def _get_connection_to_openFire(self):
        """
        Retrieves the connection details to the OpenFire server.

        Args:
            None
        Returns:
            tuple: A tuple containing the models, db, uid, and password for the OpenFire server.
        """
        url = config.get('communication_parent_url')
        db = config.get('communication_parent_db')
        username = config.get('communication_parent_username')
        password = config.get('communication_parent_password')
        common = client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        models = client.ServerProxy(f'{url}/xmlrpc/2/object')
        return models, db, uid, password

    @api.model
    def _cron_communication_message_between_customer_and_base(self):
        """
        This method is responsible for performing various tasks related to communication messages between
        the customer and the base. It executes the following steps:

        1. Update edited message from the parent database.
        2. Unlink messages that are not in the parent database.
        3. Unlink messages that are in edition in the parent database.
        4. Unlink the old messages.
        5. Create new message from the parent database.

        Args:
            None
        Returns:
            None
        """
        self._update_edited_message()
        self._unlink_missing_in_parent()
        self._unlink_in_edition_message()
        self._unlink_old_message()
        self._create_new_message()
