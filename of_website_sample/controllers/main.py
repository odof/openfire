# -*- coding: utf-8 -*-
import json
import logging
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http, tools, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.base.ir.ir_qweb.fields import nl2br
from odoo.addons.website.models.website import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.exceptions import ValidationError
from odoo.addons.website_form.controllers.main import WebsiteForm

_logger = logging.getLogger(__name__)

class WebsiteSaleSample(WebsiteSale):


    # Techniquement on pourrait utiliser le controller /shop/cart/update car celui ne diffère en rien mais il sera amener à évoluer
    @http.route(['/shop/cart/sample_update'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_sample_update(self, product_id, add_qty=1, set_qty=0, **kw):
        print('cart_sample_update')
        print(self)

        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            attributes=self._filter_attributes(**kw),
        )
        return request.redirect("/shop/cart")
