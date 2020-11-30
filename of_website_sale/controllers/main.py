# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale as website_sale
from odoo.addons.website_sale_options.controllers.main import WebsiteSaleOptions as website_sale_options


class WebsiteSale(website_sale):

    def _get_search_domain(self, search, category, attrib_values):
        domain = request.website.sale_product_domain()
        if search:
            for srch in search.split(" "):
                domain += [
                    '|', '|', ('website_name', 'ilike', srch), ('website_description', 'ilike', srch),
                    ('product_variant_ids.default_code', 'ilike', srch)]

        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        return domain


class WebsiteSaleOptions(website_sale_options):

    @http.route(['/shop/cart/update_option'], type='http', auth="public", methods=['POST'], website=True,
                multilang=False)
    def cart_options_update_json(self, product_id, add_qty=1, set_qty=0, goto_shop=None, lang=None, **kw):
        if lang:
            request.website = request.website.with_context(lang=lang)

        order = request.website.sale_get_order(force_create=True)
        if order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order(force_create=True)
        product = request.env['product.product'].browse(int(product_id))

        option_ids = product.optional_product_ids.mapped('product_variant_ids').ids
        optional_product_ids = []
        for k, v in kw.items():
            if "optional-product-" in k and int(kw.get(k.replace("product", "add"))) and int(v) in option_ids:
                optional_product_ids.append((int(v), int(kw.get(k.replace("product", "add")))))

        attributes = self._filter_attributes(**kw)

        if add_qty or set_qty:
            order._cart_update(
                product_id=int(product_id),
                add_qty=add_qty,
                set_qty=set_qty,
                attributes=attributes
            )

        # options have all time the same quantity
        for option_id, option_qty in optional_product_ids:
            order._cart_update(
                product_id=option_id,
                add_qty=option_qty,
                attributes=attributes,
            )

        return str(order.cart_quantity)
