# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

import requests

from odoo import models


class ESBService(models.Model):
    _inherit = "of.esb.service"

    def get_data_firebase(self, args):
        return []

    def set_data_firebase(self, args):
        """
        Expected data_in format to send a push notification:
        {
            "notifications": [
                {
                    "type": "message",
                    "title": "Title",
                    "message": "Message",
                    "registrations": ["registration_token1", "registration_token2"]
                },
                {
                    "type": "data",
                    "data": {
                        "key1": "value1",
                        "key2": "value2"
                    },
                    "registrations": ["registration_token1", "registration_token2"]
                }
            ]
        }

        """
        if connection := self.env.ref("of_esb_firebase.connection_firebase"):
            token = connection.connect()
            in_data = json.loads(args.in_data)
            notifications = in_data.get("notifications", False) if in_data else []
            for notification in notifications:
                ttype = notification.get("type", False)
                title = notification.get("title", False)
                message = notification.get("message", False)
                data = notification.get("data", {})

                # Fcm does not accept dictionary values that are not strings, so we need to convert them
                data_stringified = self._stringify_dictionary_values(data)

                registrations = notification.get("registrations", False)
                if ttype == "message":
                    for registration in registrations:
                        self._send_push_notification(
                            token,
                            title,
                            message,
                            data_stringified,
                            registration,
                        )
                elif ttype == "data":
                    for registration in registrations:
                        self._send_data_notification(
                            token,
                            data_stringified,
                            registration,
                        )
        return True

    def _send_data_notification(self, token, data, target_token):
        url = self._build_send_message_url()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; UTF-8",
        }
        payload = {
            "message": {
                "token": target_token,
                "data": data,
                "android": {
                    "priority": "high",
                },
            }
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        return response.json()

    def _send_push_notification(self, token, title, body, data, target_token):
        url = self._build_send_message_url()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; UTF-8",
        }
        payload = {
            "message": {
                "token": target_token,
                "android": {
                    "priority": "high",
                },
                "data": data,
                "notification": {
                    "title": title,
                    "body": body,
                },
            }
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        return response.json()

    def _build_send_message_url(self):
        connection = self.env.ref("of_esb_firebase.connection_firebase")
        if connection.firebase_environment == "development":
            return "https://fcm.googleapis.com/v1/projects/openfiremobiledebug/messages:send"
        else:
            return "https://fcm.googleapis.com/v1/projects/openfiremobile/messages:send"

    def _stringify_dictionary_values(self, dictionary):
        return {key: str(value) for key, value in dictionary.items() if value}
