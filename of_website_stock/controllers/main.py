# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http, fields, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from datetime import datetime


class WebsiteSaleStockNotify(http.Controller):

    @http.route('/website_sale_stock_notify/notify', type='json', auth="public", methods=['POST'], website=True)
    def notify(self, product_id, email, **post):
        cr, uid, context = request.cr, request.uid, request.context
        notification = request.env['of.website.stock.notify']
        request.env.uid = 1
        if uid != request.website.user_id.id:
            user_brw = request.env['res.users'].browse(uid)
            notification_ids = notification.search([('product_id', '=', int(product_id)), ('email', '=', email)])
            if not notification_ids:
                notification.create(
                    {'partner_id': user_brw.partner_id.id, 'product_id': product_id, 'email': email})

        else:
            notification_ids = notification.search([('product_id', '=', int(product_id)), ('email', '=', email)])
            if not notification_ids:
                notification.create({'product_id': product_id, 'email': email})

        return True


class WebsiteSaleDelivery(WebsiteSale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        order = request.website.sale_get_order()
        requested_date = post.get('requested_date')
        if requested_date:
            requested_date = datetime.strptime(requested_date, '%d/%m/%Y')
            if order:
                order.requested_date = requested_date
                return request.redirect("/shop/payment")

        for line in order.order_line:
            line.customer_lead = line.product_id.sale_delay

        order._compute_of_website_commitment_date()

        return super(WebsiteSaleDelivery, self).payment(**post)
