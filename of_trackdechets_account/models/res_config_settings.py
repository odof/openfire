# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import urllib.parse

from odoo import fields, models
from odoo.tools import config

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_trackdechets_account_api_token = fields.Char(
        string="(OF) Trackdechets API Token",
        config_parameter="of_trackdechets_account.api_token",
    )

    def action_redirect_to_trackdechets_authentication(self):
        trackdechets_app_url = config.get("of_trackdechets_app_url")
        trackdechets_client_id = config.get("of_trackdechets_client_id")
        if not trackdechets_app_url or not trackdechets_client_id:
            _logger.error(
                "The configuration keys 'of_trackdechets_api_url' or 'of_trackdechets_client_id' are missing in "
                "odoo.conf"
            )
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        encoded_redirect_uri = urllib.parse.quote(f"{base_url}/trackdechets_account/authentication")

        trackdechets_oauth_url = (
            f"{trackdechets_app_url}/oauth2/authorize/dialog?"
            f"client_id={trackdechets_client_id}&response_type=code&redirect_uri={encoded_redirect_uri}"
        )
        return {
            "type": "ir.actions.act_url",
            "url": trackdechets_oauth_url,
            "target": "self",
        }
