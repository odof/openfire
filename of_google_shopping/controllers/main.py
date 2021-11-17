# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class OfGoogleShoppingController(http.Controller):

    @http.route(['/wedig_google_shopping_xml'], type='http', auth='user', website=True)
    def google_shopping_xml(self):
        xml = request.env['of.google.shopping'].create_xml_file()
        response = request.make_response(
            xml, headers=[
                ('Content-Type', 'application/xml'),
                ('Content-Disposition', 'attachment; filename=wedig_google_shopping.xml;')])

        return response
