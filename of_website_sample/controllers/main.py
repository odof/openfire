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
from werkzeug.exceptions import Forbidden, NotFound
from odoo.exceptions import ValidationError, UserError
from odoo.addons.website_form.controllers.main import WebsiteForm

_logger = logging.getLogger(__name__)


class WebsiteSaleSample(WebsiteSale):

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)

        # Si un échantillon apparait déjà dans le panier, on n'en rajoute pas plus
        for line in sale_order.order_line:
            if line.product_id.id == int(product_id) and line.product_id.of_is_sample:
                return request.redirect("/shop/cart")

        sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            attributes=self._filter_attributes(**kw),
        )
        return request.redirect("/shop/cart")

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):

        res = super(WebsiteSaleSample, self).product(product, category, search, **kwargs)

        if kwargs.get('invalid', False):
            res.__dict__['qcontext']['invalid'] = int(kwargs.get('invalid'))

        return res
