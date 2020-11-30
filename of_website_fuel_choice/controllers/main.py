# -*- coding: utf-8 -*-

import logging
from odoo import http, tools
from odoo.http import request
from mapbox import Geocoder
from odoo.addons.of_utils.models.of_utils import voloiseau


_logger = logging.getLogger(__name__)


class OFWebsiteFuelChoice(http.Controller):

    @http.route(['/fuel_choice'], type='http', auth="public", website=True)
    def fuel_choice(self, **kw):
        values = kw
        error = dict()
        validated = False
        email = 'email' in values and values.get('email') or False
        fuel = 'fuel_id' in values and values['fuel_id'] != '' and request.env['of.website.product.fuel'].browse(
            int(values['fuel_id']))
        checkout = 'checkout_id' in values and values['checkout_id'] != '' and \
            request.env['of.website.product.fuel.checkout.mode'].browse(int(values['checkout_id']))

        if 'submitted' in values:
            error_message = []
            if not fuel:
                error['fuel_id'] = 'error'
            if values.get('qty') and int(values.get('qty')) <= 0:
                error['qty'] = 'error'
            if not checkout:
                error['checkout_id'] = 'error'
            elif checkout.type == 'delivery':
                if not values.get('street'):
                    error['street'] = 'error'
                if not values.get('zip'):
                    error['zip'] = 'error'
                if not values.get('city'):
                    error['city'] = 'error'
            if values.get('action') == 'send':
                # email validation
                if values.get('email') and not tools.single_email_re.match(values.get('email')):
                    error['email'] = 'error'
                    error_message.append(u"Courriel invalide ! Merci de renseigner une adresse valide.")

            if error:
                error['error_message'] = [u"Certains champs ne sont pas correctement remplis"]
                error['error_message'] += error_message
            else:
                validated = True

        if validated and values.get('action') == 'order':
            # Find corresponding product
            product_qty_list = []
            lines = fuel.line_ids
            if len(fuel.line_ids) > 1:
                if values.get('length'):
                    lines = lines.filtered(lambda l: l.length == values.get('length'))
                if 'split' in values:
                    lines = lines.filtered(lambda l: l.split)
                else:
                    lines = lines.filtered(lambda l: not l.split)
            product = lines and lines[0].product_id or False

            if product:
                # Add product to cart with corresponding quantity
                product_qty_list.append((product, float(values.get('qty'))))

                # Handle checkout mode
                if checkout.product_id:
                    product_qty_list.append((checkout.product_id, 1.0))
                elif checkout.line_ids:
                    # Get GPS coordinates
                    distance_error = False
                    server_token = tools.config.get("of_token_mapbox", "")
                    if not server_token:
                        distance_error = True
                    else:
                        geocoder = Geocoder(access_token=server_token)

                        result = False
                        try:
                            result = geocoder.forward(
                                "%s %s %s France" % (values.get('street'), values.get('zip'), values.get('city'))).\
                                json()
                        except Exception:
                            distance_error = True

                        if not result or not result.get('features'):
                            distance_error = True
                        else:
                            res = result.get('features')[0]
                            if res:
                                coords = res.get("center", {})
                                if coords:
                                    lat = coords[1]
                                    lng = coords[0]
                                else:
                                    distance_error = True
                            else:
                                distance_error = True
                    if distance_error:
                        validated = False
                        error['error_message'] = [u"Nous sommes désolé mais nous parvenons pas à situer votre adresse, "
                                                  u"merci de formuler votre demande par courriel"]
                    else:
                        # Calculate distance
                        company = request.env['res.company'].sudo().browse([1])
                        company_lat = company.geo_lat
                        company_lng = company.geo_lng
                        distance = voloiseau(lat, lng, company_lat, company_lng)

                        # Find corresponding checkout mode line
                        line = checkout.line_ids.filtered(lambda l: l.min_distance <= distance < l.max_distance)
                        if line:
                            line = line[0]
                            product_qty_list.append((line.product_id, 1.0))
                        else:
                            validated = False
                            error['error_message'] = [u"Nous sommes désolé mais votre adresse n'est pas située dans nos"
                                                      u" zones de livraisons, merci de modifier votre mode de retrait "
                                                      u"ou de formuler votre demande par courriel"]

                if validated:
                    if len(product_qty_list) > 1:
                        # Create kit
                        kit_vals = {'of_pricing': 'computed'}
                        lines = []
                        for product_rec, product_qty in product_qty_list:
                            if product_rec.sudo().of_is_kit:
                                for line in product_rec.sudo().kit_line_ids:
                                    kit_line_vals = {
                                        'product_id': line.product_id.id,
                                        'product_uom_id': line.product_uom_id.id,
                                        'qty_per_kit': line.product_qty * product_qty,
                                        'sequence': line.sequence,
                                        'name': line.product_id.sudo().name_get()[0][1] or line.product_id.sudo().name,
                                        'price_unit': line.product_id.sudo().list_price,
                                        'cost_unit': line.product_id.sudo().standard_price,
                                        'customer_lead': line.product_id.sudo().sale_delay}
                                    lines.append((0, 0, kit_line_vals))
                            else:
                                kit_line_vals = {
                                    'product_id': product_rec.id,
                                    'product_uom_id': product_rec.sudo().uom_id.id,
                                    'qty_per_kit': product_qty,
                                    'name': product_rec.sudo().name_get()[0][1] or product_rec.sudo().name,
                                    'price_unit': product_rec.sudo().list_price,
                                    'cost_unit': product_rec.sudo().standard_price,
                                    'customer_lead': product_rec.sudo().sale_delay}
                                lines.append((0, 0, kit_line_vals))
                        kit_vals['kit_line_ids'] = lines
                        kit_vals['qty_order_line'] = 1.0
                        new_kit = request.env['of.saleorder.kit'].sudo().create(kit_vals)
                        # Create order line
                        order = request.website.sale_get_order(force_create=1)
                        order_line = request.env['sale.order.line'].new({
                            'product_id': product.id,
                            'product_uom_qty': 1.0,
                            'order_id': order.id,
                            'kit_id': new_kit.id,
                            'of_is_kit': True,
                            'of_pricing': 'computed',
                        })
                        order_line.sudo().product_id_change()
                        order_line.sudo()._onchange_kit_id()
                        order_line_vals = order_line._convert_to_write(order_line._cache)
                        order_line_vals['name'] = \
                            "%s %s + %s" % (values.get('qty'), product.sudo().name, product_qty_list[-1][0].sudo().name)
                        order_line = request.env['sale.order.line'].sudo().create(order_line_vals)
                    else:
                        res = request.website.sale_get_order(force_create=1)._cart_update(
                            product_id=int(product_qty_list[0][0].id), add_qty=product_qty_list[0][1])
                        order_line = request.env['sale.order.line'].browse(res['line_id'])
                    order_line.of_fuel_choice = True
                    # Handle storage checkout
                    if checkout.type == 'storage':
                        order_line.of_storage = True
                    # Redirect to cart summary
                    return request.redirect('/shop/cart')

            else:
                validated = False
                error['error_message'] = [u"Nous sommes désolé mais aucun article ne correspond à vos critères, "
                                          u"merci de formuler votre demande par courriel"]
        elif validated and values.get('action') == 'email':
            validated = False
            email = True
        elif validated and values.get('action') == 'send':
            # Send info by mail
            mail_template = request.env['ir.model.data'].sudo().get_object(
                'of_website_fuel_choice', 'of_website_fuel_choice_mail_template')
            company = request.env['res.company'].sudo().browse([1])
            mail_template.body_html = \
                u"<p>Bonjour,</p>" \
                u"<p>" \
                u"Une demande de devis de combustible a été effectuée sur le site internet :<br/>" \
                u"- Type de bois : %s<br/>" % fuel.name
            if values.get('length'):
                mail_template.body_html += u"&nbsp;&nbsp;&nbsp;&nbsp;- Longueur : %s<br/>" % values.get('length')
            if len(list(set(fuel.line_ids.mapped('split')))) > 1:
                mail_template.body_html += u"&nbsp;&nbsp;&nbsp;&nbsp;- Fendu : %s<br/>" % \
                                           (u"oui" if 'split' in values else u"non")
            mail_template.body_html += u"- Quantité : %s<br/>" % values.get('qty')
            mail_template.body_html += u"- Mode de retrait : %s<br/>" % checkout.name
            if checkout.type == 'delivery':
                mail_template.body_html += u"&nbsp;&nbsp;&nbsp;&nbsp;- Rue : %s<br/>" % values.get('street')
                mail_template.body_html += u"&nbsp;&nbsp;&nbsp;&nbsp;- Code postal : %s<br/>" % values.get('zip')
                mail_template.body_html += u"&nbsp;&nbsp;&nbsp;&nbsp;- Ville : %s<br/>" % values.get('city')
            mail_template.body_html += u"</p>"
            mail_template.body_html += u"<p>Adresse du contact : %s</p>" % values.get('email')
            mail_template.send_mail(company.id)

            values = {
                'fuel_types': request.env['of.website.product.fuel'].search([]),
                'fuel': False,
                'checkout_modes': request.env['of.website.product.fuel.checkout.mode'].search([]),
                'checkout': False,
                'email': False,
                'values': dict(),
                'error': dict(),
                'send_message': u"Une demande de devis nous a bien été transmise, "
                                u"vous serez recontacté dans les plus brefs délais."
            }
            return request.render("of_website_fuel_choice.fuel_choice", values)

        if not validated:
            values = {
                'fuel_types': request.env['of.website.product.fuel'].search([]),
                'fuel': fuel,
                'checkout_modes': request.env['of.website.product.fuel.checkout.mode'].search([]),
                'checkout': checkout,
                'email': email,
                'values': values,
                'error': error,
            }
            return request.render("of_website_fuel_choice.fuel_choice", values)

    @http.route(['/fuel_choice/fuel_infos/<model("of.website.product.fuel"):fuel>'], type='json', auth="public",
                methods=['POST'], website=True)
    def fuel_infos(self, fuel, **kw):
        return dict(
            lengths=filter(None, list(set(fuel.line_ids.mapped('length')))),
            splits=list(set(fuel.line_ids.mapped('split'))),
        )

    @http.route(['/fuel_choice/checkout_infos/<model("of.website.product.fuel.checkout.mode"):checkout>'], type='json',
                auth="public", methods=['POST'], website=True)
    def checkout_infos(self, checkout, **kw):
        return dict(
            delivery=(checkout.type == 'delivery'),
        )
