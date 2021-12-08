# -*- coding: utf-8 -*-

from odoo.addons.website_quote.controllers.main import sale_quote
from odoo import http, fields
from odoo.http import request


class OFSaleQuote(sale_quote):

    @http.route(['/quote/accept'], type='json', auth="public", website=True)
    def accept(self, order_id, token=None, signer=None, signer_email=None, sign_date=None, sign=None, **post):
        order = request.env['sale.order'].sudo().browse(order_id)
        if token != order.access_token or order.require_payment:
            return request.render('website.404')
        if order.state != 'sent':
            return False
        if order.partner_id.email != signer_email:
            return 5
        order.write({'of_signer': signer,
                     'of_customer_signature': sign,
                     'of_signature_date': fields.Datetime.now()})

        template = request.env.ref('of_sale_quote_template.of_sale_order_signed_email_template')
        order.message_post_with_template(template.id)

        order.action_confirm()

        return True
