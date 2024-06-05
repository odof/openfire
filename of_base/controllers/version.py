# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http


class OFBaseVersion(http.Controller):
    @http.route('/openfire/version', type='json', auth='public')
    def get_openfire_version(self):
        version = http.request.env['ir.config_parameter'].sudo().get_param('openfire.version')
        return {'version': version}
