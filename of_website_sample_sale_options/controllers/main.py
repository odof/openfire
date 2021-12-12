# -*- coding: utf-8 -*-
import json
from odoo import http, tools, _
from odoo.http import request
from odoo.addons.website_sale_options.controllers.main import WebsiteSaleOptions


class OfWebsiteSaleOptions(WebsiteSaleOptions):

    @http.route(['/shop/modal'], type='json', auth="public", methods=['POST'], website=True)
    def modal(self, product_id, **kw):
        product = request.env['product.product'].sudo().browse(int(product_id))

        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)

        # On ne mélange pas des échantillons et des produits dans un même panier
        if sale_order.order_line and sale_order.order_line[0].product_id.of_is_sample != product.of_is_sample:
            return request.env['ir.ui.view'].render_template("of_website_sample_sale_options.modal_error", {})

        return super(OfWebsiteSaleOptions, self).modal(product_id, **kw)
