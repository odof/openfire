# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests

from odoo import models

OVH_HTTP_ENDPOINT = "https://www.ovh.com/cgi-bin/sms/http2sms.cgi"


class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    def _prepare_ovh_http_params(self, account, message, sms_id):
        sms = self.env['sms.sms'].browse(sms_id)
        return {
            'smsAccount': account.sms_ovh_http_account,
            'login': account.sms_ovh_http_login,
            'password': account.sms_ovh_http_password,
            'from': sms.of_sender_id.name or account.sms_ovh_http_from,
            'to': sms.number,
            'message': message,
            'noStop': '0' if sms.of_is_commercial else '1',
        }

    def _send_sms_with_ovh_http(self, number, message, sms_id):
        # Try to return same error code like odoo
        # list is here: self.IAP_TO_SMS_STATE
        if not number:
            return "wrong_number_format"
        account = self._get_sms_account()
        r = requests.get(
            OVH_HTTP_ENDPOINT,
            params=self._prepare_ovh_http_params(account, message, sms_id),
        )
        response = r.text
        if response[:2] != "OK":
            self.env["sms.sms"].browse(sms_id).error_detail = response
            return 'server_error'
        return 'success'
