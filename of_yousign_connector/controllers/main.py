# -*- coding: utf-8 -*-

import hashlib
import hmac
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OFControllersYousign(http.Controller):

    def _compare_signature(self, sandbox=True):
        signature = request.httprequest.headers.environ.get('HTTP_X_YOUSIGN_SIGNATURE_256')
        db_signature = (
            request
            .env['ir.config_parameter'].sudo()
            .get_param('yousign.%s.webhook.secret' % (sandbox and 'sandbox' or 'prod'), "")
        )
        data = request.httprequest.get_data().decode(request.httprequest.charset)
        digest = hmac.new(db_signature.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
        computed_signature = "sha256={digest}".format(digest=digest)
        return hmac.compare_digest(signature, computed_signature)

    def _make_response(self, code, message):
        return {
            "code": code,
            "message": message,
        }

    @http.route(['/yousign_sandbox_webhook'], methods=['POST'], type='json', auth="none", csrf=False)
    def handle_yousign_sandbox_data(self, **kw):
        if not self._compare_signature():
            _logger.debug("Yousign webhook : invalid sandbox webhook signature")
            return self._make_response(401, "invalid webhook signature")
        self._validate_body(request.get_json_data())
        return self._make_response(200, "OK")

    @http.route(['/yousign_webhook'], methods=['POST'], type='json', auth="none", csrf=False)
    def handle_yousign_data(self, **kw):
        if not self._compare_signature(sandbox=False):
            _logger.debug("Yousign webhook : invalid webhook signature")
            return self._make_response(401, "invalid webhook signature")
        self._validate_body(request.get_json_data())
        return self._make_response(200, "OK")

    def _validate_body(self, body):
        signature_data = body.get('data', {}).get('signature_request')
        if not signature_data:
            return False
        signature_id = signature_data['id']
        signature_request = request.env['of.yousign.request'].sudo().search([('ys_identifier', '=', signature_id)])
        if not signature_request:
            return False
        vals = {
            'state': signature_data['status'] == 'done' and 'signed' or 'cancel',
            'last_status_update' : fields.Datetime.now(),
        }
        signers_vals = []
        signers_data = signature_data['signers']
        for signer_data in signers_data:
            status = signer_data.get('status')
            signer_id = signer_data.get('id')
            signer = signature_request.signatory_ids.filtered(lambda r: r.ys_identifier == signer_id)
            if not signer:
                continue
            signers_vals.append(
                (
                    1,
                    signer.id,
                    {'state': status == 'signed' and 'signed' or 'refused'}
                )
            )
        if signers_vals:
            vals['signatory_ids'] = signers_vals
        return signature_request.write(vals)
