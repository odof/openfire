# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from xmlrpc import client

from odoo import api, fields, models
from odoo.tools import config


class OfCommunicationCustomer(models.Model):
    """
    Class Model qui permet de récupérer un message(note de patch, alerte de maintenance, etc.) de la base parent
    """

    _inherit = "of.communication"

    active = fields.Boolean(string="Archived", default=True, readonly=True)
    source_message_id = fields.Integer(string='Source Message ID', readonly=True)

    def _get_connection_to_openFire(self):
        """
        Fonction qui permet de récupérer les données pour se connecter à la base pare
        """
        url = config.get('communication_parent_url')
        db = config.get('communication_parent_db')
        username = config.get('communication_parent_username')
        password = config.get('communication_parent_password')

        common = client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        models = client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        return models, db, uid, password

    def _create_new_message(self):
        """
        La fonction récupère les messages dont l'état est "publié" dans la base parent,
        mais qui ne sont pas présents dans la base enfant.
        Elle sélectionne également ceux dont la date et l'heure de publication sont antérieures,
        mais dont la date et l'heure de fin de publication n'est pas encore passée,
        puis les transfère vers la base enfant pour y être créés.
        """
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
        """
        La fonction récupère les messages dont l'état est "publié" et éditer dans la base parent,
        et qui sont présents dans la base enfant.
        Elle sélectionne également ceux dont la date et l'heure de publication sont antérieures,
        mais dont la date et l'heure de fin de publication n'est pas encore passée,
        puis les modifie sur la base enfant et met l'édition a "false" sur la base parent.
        """
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

    def _unlink_edited_message(self):
        """
        La fonction récupère les messages dont l'état est "publié" et éditer dans la base parent,
        et qui sont présents dans la base enfant.
        Elle sélectionne également ceux dont la date et l'heure de publication sont antérieures,
        mais dont la date et l'heure de fin de publication n'est pas encore passée,
        puis les supprime sur la base enfant.
        """
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
                    ('edited', '=', True),
                ]
            ],
            {'fields': []},
        )

        for message in parent_messages:
            child_message = existing_messages.filtered(lambda r: r.source_message_id == message['id'])
            child_message.with_context(of_force_message_delete=True).unlink()

    def _unlink_old_message(self):
        """
        La fonction récupère les messages dont la date et l'heure de fin de publication sont antérieures,
        puis les supprime sur la base enfant.
        """
        now = fields.Datetime.now()
        existing_messages = self.search(
            [
                ('state', '=', 'published'),
                ('end_scheduled_publication', '<=', now),
            ]
        )

        for message in existing_messages:
            message.with_context(of_force_message_delete=True).unlink()

    @api.model
    def _cron_communication_message_between_customer_and_base(self):
        """
        La fonction cron se lance toute les 5 minute et execute toute les fonctions
        """
        self._create_new_message()
        self._update_existing_message()
        self._unlink_edited_message()
        self._unlink_old_message()
