# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_form.controllers.main import WebsiteForm


class OFWebsiteForm(WebsiteForm):

    @http.route('/website_form/<string:model_name>', type='http', auth="public", methods=['POST'], website=True)
    def website_form(self, model_name, **kwargs):
        if model_name == 'crm.lead':
            partner = request.env['res.partner']

            if 'email_from' in request.params:
                email = request.params['email_from']
                partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)

            if not partner and 'phone' in request.params:
                phone = request.params['phone']
                partner = request.env['res.partner'].sudo().search(
                    [('of_phone_number_ids.number', 'ilike', phone)], limit=1)

            if partner:
                request.params['partner_id'] = partner.id
                request.params['user_id'] = partner.user_id.id
            else:
                default_user_id = request.env['ir.model.data'].xmlid_to_res_id('of_website_crm.of_default_user')
                partner = request.env['res.partner'].sudo().create({'name': request.params['contact_name'],
                                                                    'email': request.params.get('email_from', False),
                                                                    'phone': request.params.get('phone', False),
                                                                    'user_id': default_user_id})
                request.params['partner_id'] = partner.id
                request.params['user_id'] = default_user_id
                request.params['Nouveau contact'] = u"Oui"

            if 'email_from' in request.params:
                request.params['E-mail'] = request.params['email_from']
                request.params.pop('email_from')
            if 'phone' in request.params:
                request.params['Telephone'] = request.params['phone']
                request.params.pop('phone')

        return super(OFWebsiteForm, self).website_form(model_name, **kwargs)
