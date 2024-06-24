# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json

import google.auth.transport.requests
from google.oauth2 import service_account

from odoo import fields, models


class ESBConnection(models.Model):
    _inherit = "of.esb.connection"

    ttype = fields.Selection(selection_add=[("firebase", "Firebase")])
    firebase_environment = fields.Selection(
        selection=[("development", "Development"), ("production", "Production")],
        default="production",
    )
    firebase_service_account_file = fields.Binary(string="Service Account File", required=True)

    def connect_firebase(self):
        account_file_decoded = base64.b64decode(self.firebase_service_account_file)
        account_file_parsed = json.loads(account_file_decoded)
        credentials = service_account.Credentials.from_service_account_info(account_file_parsed)

        scoped_credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])

        auth_request = google.auth.transport.requests.Request()
        scoped_credentials.refresh(auth_request)
        return scoped_credentials.token
