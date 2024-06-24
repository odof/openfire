# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import json
import logging

import requests

from odoo import api, fields, models
from odoo.tools import config

from odoo.addons.bus.models.bus import DEFAULT_SERVER_DATETIME_FORMAT, TIMEOUT

logger = logging.getLogger(__name__)


class BusBus(models.Model):
    _inherit = "bus.bus"

    of_keep = fields.Boolean()

    @api.autovacuum
    def _gc_messages(self):
        timeout_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=TIMEOUT * 2)
        domain = [("create_date", "<", timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ("of_keep", "=", False)]
        return self.sudo().search(domain).unlink()

    @api.model
    def clean_notification(self):
        """Cette fonction sert juste à supprimer les notifications qui seraient encore présentes mais qu'on
        ne souhaite pas envoyer ou qui causent des erreurs"""
        timeout_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=TIMEOUT * 2)
        domain = [("create_date", "<", timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
        return self.sudo().search(domain).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("message"):
                message = json.loads(vals["message"])
                if message["type"] == "firebase":
                    # Si c'est un message de type firebase, on ne souhaite pas le supprimer via le GC tant qu'il n'a pas
                    # relevé par le CRON
                    vals["of_keep"] = True

        return super().create(vals_list)

    @api.model
    def send_external_notif(self):
        # TODO : vérifier que l'on a bien que les notifs de cette base
        for record in self.search([("of_keep", "=", True)]):
            message = json.loads(record.message)
            if payload := message.get("payload"):
                external = message["type"]
                if hasattr(record, f"send_{external}_notif"):
                    func = getattr(record, f"send_{external}_notif")
                    if func(payload):
                        record.of_keep = False

    def send_firebase_notif(self, payload):
        esb_url = config.get("of_esb_url", "")
        esb_webhook_firebase_user = config.get("of_esb_webhook_firebase_user", "")
        esb_webhook_firebase_password = config.get("of_esb_webhook_firebase_password", "")
        if not esb_url or not esb_webhook_firebase_user or not esb_webhook_firebase_password:
            logger.warning("ESB URL or Webhook Firebase User or Webhook Firebase Password is not set.")
            return False

        user = self.env["res.users"].browse(payload.get("user_id"))
        kind = payload.get("kind")

        if registration_ids := user.mapped("of_fcm_token_ids.token"):
            headers = {
                "Content-Type": "application/json",
            }

            try:
                body = {}

                if kind == "message_with_data":
                    body = {
                        "user": esb_webhook_firebase_user,
                        "password": esb_webhook_firebase_password,
                        "notifications": [
                            {
                                "type": "message",
                                "registrations": registration_ids,
                                "title": payload.get("title"),
                                "message": payload.get("message"),
                                "data": payload.get("payload", {}),
                            }
                        ],
                    }
                else:
                    body = {
                        "user": esb_webhook_firebase_user,
                        "password": esb_webhook_firebase_password,
                        "notifications": [
                            {
                                "type": "data",
                                "registrations": registration_ids,
                                "data": payload.get("payload", {}),
                            }
                        ],
                    }
                requests.post(f"{esb_url}/webhook/firebase", headers=headers, data=json.dumps(body), timeout=10)
            except Exception as e:
                logger.info(f"Error while generating FCM Notification. {e}")
        return True
