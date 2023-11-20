# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class GeoCoder(models.AbstractModel):
    _inherit = 'base.geocoder'

    @api.model
    def _call_openstreetmap(self, addr, **kw):
        """
        Override to add a timeout

        Use Openstreemap Nominatim service to retrieve location
        :return: (latitude, longitude) or None if not found
        """
        timeout_value = int(self.env['ir.config_parameter'].sudo().get_param('of.geolocalize.timeout', 10))
        if not addr:
            _logger.info('invalid address given')
            return None
        url = 'https://nominatim.openstreetmap.org/search'
        try:
            headers = {'User-Agent': 'Odoo (http://www.odoo.com/contactus)'}
            response = requests.get(
                url,
                headers=headers,
                params={'format': 'json', 'q': addr},
                timeout=timeout_value,
            )
            _logger.info('openstreetmap nominatim service called')
            if response.status_code != 200:
                _logger.warning(
                    'Request to openstreetmap failed.\nCode: %s\nContent: %s', response.status_code, response.content
                )
            result = response.json()
        except Exception as e:
            self._raise_query_error(e)
        geo = result[0]
        return float(geo['lat']), float(geo['lon']), result
