# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.of_web_api.controllers.main import OFAPIWeb


class OFAPIWebCRM(OFAPIWeb):

    def create_record(self, model_name, vals):
        u"""Héritage pour éviter la duplication de partenaires"""
        if model_name == 'crm.lead':
            partner = request.env['res.partner']

            if 'email_from' in vals:
                email = vals['email_from']
                partner = partner.sudo().search([('email', '=', email)], limit=1)

            if not partner and 'phone' in vals:
                phone = vals['phone']
                partner = partner.sudo().search([('of_phone_number_ids.number', 'ilike', phone)], limit=1)

            if not partner and 'mobile' in vals:
                mobile = vals['mobile']
                partner = partner.sudo().search([('of_phone_number_ids.number', 'ilike', mobile)], limit=1)

            if partner:
                vals['partner_id'] = partner.id
                vals['user_id'] = partner.user_id.id
            else:
                api_user_id = request.env['ir.model.data'].xmlid_to_res_id('of_web_api.of_api_user')
                partner = request.env['res.partner'].sudo(api_user_id).create(
                    {'name': vals.get('contact_name', vals.get('name')),
                     'email': vals.get('email_from', False),
                     'phone': vals.get('phone', False),
                     'user_id': api_user_id})
                vals['partner_id'] = partner.id
                vals['user_id'] = api_user_id
        return super(OFAPIWebCRM, self).create_record(model_name, vals)
