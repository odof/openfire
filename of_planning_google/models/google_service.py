# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import urllib2

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'


class GoogleService(models.TransientModel):
    _inherit = 'google.service'

    # TODO JEM : remove preuri param, and rename type into method
    @api.model
    def _do_request(self, uri, params={}, headers={}, type='POST', preuri="https://www.googleapis.com"):
        """ Execute the request to Google API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
            :param uri : the url to contact
            :param params : dict or already encoded parameters for the request to make
            :param headers : headers of request
            :param type : the method to use to make the request
            :param preuri : pre url to prepend to param uri.
        """

        status = 418
        response = ""
        ask_time = fields.Datetime.now()
        try:
            status, response, ask_time = super(GoogleService, self)._do_request(uri, params, headers, type, preuri)
        except urllib2.HTTPError, error:
            if error.code in (204, 404):
                status = error.code
                response = ""
            else:
                _logger.exception("Bad google request : %s !", error.read())
                if error.code in (400, 401, 410):
                    raise error
                raise self.env['res.config.settings'].get_config_warning(
                    _(u"Something went wrong with your request to google"))
        except UserError, e:
            # exception raised from parent function is a UserError so we can't catch code 403
            raise e
        return status, response, ask_time
