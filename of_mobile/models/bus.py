# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import json
import logging

from pyfcm import FCMNotification

from odoo import api, fields, models
from odoo.tools import config

from odoo.addons.bus.models.bus import DEFAULT_SERVER_DATETIME_FORMAT, TIMEOUT

logger = logging.getLogger(__name__)


class BusBus(models.Model):
    _inherit = 'bus.bus'

    of_keep = fields.Boolean()

    @api.autovacuum
    def _gc_messages(self):
        timeout_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=TIMEOUT * 2)
        domain = [('create_date', '<', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('of_keep', '=', False)]
        return self.sudo().search(domain).unlink()

    @api.model
    def clean_notification(self):
        # cette fonction sert juste à supprimer les notifications qui seraient encore présentes mais qu'on
        # ne souhaite pas envoyer ou qui causent des erreurs
        timeout_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=TIMEOUT * 2)
        domain = [('create_date', '<', timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
        return self.sudo().search(domain).unlink()

    @api.model
    def create(self, vals):
        # on hérite la fonction ici pour vérifier si le message est de type firebase et si oui, on passe la
        # variable keep à True, pour que le GC ne supprime pas le message tant qu'il n'a pas été relevé par
        # le CRON
        if vals.get('message'):
            message = json.loads(vals['message'])
            if message['type'] == "firebase":
                vals['of_keep'] = True

        return super().create(vals)

    @api.model
    def send_external_notif(self):
        # TODO : vérifier que l'on a bien que les notifs de cette base
        for record in self.search([('of_keep', '=', True)]):
            message = json.loads(record.message)
            if payload := message.get('payload'):
                external = message['type']
                if hasattr(record, f"send_{external}_notif"):
                    func = getattr(record, f"send_{external}_notif")
                    if func(payload):
                        record.of_keep = False

    def send_firebase_notif(self, payload):
        of_token_fcm = config.get('of_token_fcm', '')
        if not of_token_fcm:
            logger.info("No FCM token configured")
            return False

        push_service = FCMNotification(api_key=of_token_fcm)
        user = self.env['res.users'].browse(payload.get('user_id'))
        kind = payload.get('kind')

        if registration_ids := user.mapped('of_fcm_token_ids.token'):
            try:
                if kind == 'message_with_data':
                    result = push_service.notify_multiple_devices(
                        registration_ids=registration_ids,
                        message_title=payload.get('title'),
                        message_body=payload.get('message'),
                        data_message=payload.get('payload'),
                    )
                else:
                    result = push_service.multiple_devices_data_message(
                        registration_ids=registration_ids, data_message=payload.get('payload')
                    )

                logger.info(result)
            except Exception as e:
                logger.info("Error while generating FCM Notification. %s" % (e,))
                return False
        return True
