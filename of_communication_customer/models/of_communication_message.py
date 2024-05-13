# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from xmlrpc import client

from odoo import api, fields, models


class OfCommunicationCustomer(models.Model):
    _inherit = "of.communication"

    active = fields.Boolean(string="Archived", default=True, readonly=True)
    source_message_id = fields.Integer(string='Source Message ID', readonly=True)

    def _get_connection_to_openFire(self):
        url = "http://localhost:8069"
        db = "openfire"
        username = "admin"
        password = "admin"

        common = client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        models = client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        return models, db, uid, password

    def _create_new_message(self):
        now = fields.Datetime.now()
        models, db, uid, password = self._get_connection_to_openFire()
        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('start_scheduled_publication', '<=', now),
                ('end_scheduled_publication', '>=', now),
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
                    ('id', 'not in', existing_msg_ids),
                    ('start_scheduled_publication', '<=', now),
                    ('end_scheduled_publication', '>=', now),
                    ('state', '=', 'published'),
                ]
            ],
            {'fields': []},
        )

        for message in parent_messages:
            self.create(
                {
                    'name': message['name'],
                    'date': message['date'],
                    'message_type': message['message_type'],
                    'state': 'published',
                    'start_scheduled_publication': message['start_scheduled_publication'],
                    'end_scheduled_publication': message['end_scheduled_publication'],
                    'summary': message['summary'],
                    'message': message['message'],
                    'source_message_id': message['id'],
                }
            )

    def _update_existing_message(self):
        now = fields.Datetime.now()
        models, db, uid, password = self._get_connection_to_openFire()
        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('start_scheduled_publication', '<=', now),
                ('end_scheduled_publication', '>=', now),
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
                    ('end_scheduled_publication', '>=', now),
                    ('state', '=', 'published'),
                    ('edited', '=', True),
                ]
            ],
            {'fields': []},
        )
        messages_to_update = []

        for message in parent_messages:
            child_message = existing_messages.filtered(lambda r: r.source_message_id == message['id'])
            child_message and child_message.write(
                {
                    'name': message['name'],
                    'message_type': message['message_type'],
                    'start_scheduled_publication': message['start_scheduled_publication'],
                    'end_scheduled_publication': message['end_scheduled_publication'],
                    'summary': message['summary'],
                    'message': message['message'],
                }
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
                    'edited': False,
                },
            ],
        )

    def _unlink_old_message(self):
        for record in self:
            now = fields.Datetime.now()
            models, db, uid, password = record._get_connection_to_openFire()
            existing_messages = self.search(
                [
                    ('start_scheduled_publication', '>=', now),
                    ('end_scheduled_publication', '<=', now),
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
                        ('state', '!=', 'published'),
                    ]
                ],
                {'fields': []},
            )

            for message in parent_messages:
                self.unlink()

    @api.model
    def _cron_communication_message_between_customer_and_base(self):
        self._create_new_message()
        self._update_existing_message()
        # self._unlink_old_message()
