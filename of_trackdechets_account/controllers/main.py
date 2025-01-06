# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

import requests
from werkzeug.exceptions import BadRequest

from odoo import _, http
from odoo.http import request
from odoo.tools import config

_logger = logging.getLogger(__name__)


class TrackdechetsAuth(http.Controller):
    @http.route("/trackdechets_account/authentication", type="http", auth="public")
    def oauth2callback(self, **kw):
        if kw.get("code"):
            code = kw["code"]
            trackdechets_client_id = config.get("of_trackdechets_client_id")
            trackdechets_client_secret = config.get("of_trackdechets_client_secret")
            trackdechets_api_url = config.get("of_trackdechets_api_url")

            if not trackdechets_client_secret or not trackdechets_api_url or not trackdechets_client_id:
                _logger.error(
                    "The configuration keys 'of_trackdechets_client_server', 'of_trackdechets_client_id' or "
                    "'of_trackdechets_client_id' are missing in odoo.conf"
                )
            base_url = request.env.user.get_base_url()
            redirect_uri = f"{base_url}/trackdechets_account/authentication"
            basic_auth_base64 = base64.b64encode(
                f"{trackdechets_client_id}:{trackdechets_client_secret}".encode()
            ).decode()

            headers = {
                "Authorization": f"Basic {basic_auth_base64}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            body = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
            try:
                req = requests.post(f"{trackdechets_api_url}/oauth2/token", headers=headers, data=body)
                req.raise_for_status()
                access_token = req.json()["access_token"]
                settings = request.env["res.config.settings"].create(
                    {"of_trackdechets_account_api_token": access_token}
                )
                settings.execute()
                return request.redirect("/web#model=res.config.settings&view_type=form")
            except requests.exceptions.RequestException as exc:
                raise BadRequest(_("Something went wrong during your token generation.")) from exc

        elif kw.get("error"):
            raise BadRequest(_("Something went wrong. {}").format(kw["error"]))
        else:
            raise BadRequest(_("Something went wrong."))
