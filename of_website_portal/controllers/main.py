# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.addons.website_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        service_ids = request.env['of.service'].search([
            ('recurrence', '=', True),
            ('state', 'not in', ('draft', 'done', 'cancel')),
            '|',
            ('partner_id', 'child_of', request.env.user.partner_id.id),
            ('address_id', 'child_of', request.env.user.partner_id.id)
        ])
        delivery_ids = request.env['stock.picking'].search([
            ('state', 'not in', ('draft', 'cancel')),
            ('partner_id', 'child_of', request.env.user.partner_id.id)
        ])
        values.update({
            'recurrent_count': len(service_ids),
            'delivery_count': len(delivery_ids),
        })
        return values

    @http.route(['/my/deliveries'], type='http', auth='user', website=True)
    def portal_my_deliveries(self):
        values = self._prepare_portal_layout_values()
        delivery_ids = request.env['stock.picking'].search([
            ('partner_id', 'child_of', request.env.user.partner_id.id)
        ])
        values.update({
            'deliveries': delivery_ids,
        })
        return request.render('of_website_portal.of_website_portal_portal_my_deliveries', values)

    @http.route(['/my/deliveries/pdf/<int:delivery_id>'], type='http', auth="user", website=True)
    def portal_get_delivery(self, delivery_id=None, **kw):
        delivery = request.env['stock.picking'].browse([delivery_id])
        try:
            delivery.check_access_rights('read')
            delivery.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        pdf = request.env['report'].sudo().get_pdf([delivery_id], 'stock.report_deliveryslip')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Bon_de_livraison.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/of_contracts'], type='http', auth='user', website=True)
    def portal_my_of_contracts(self):
        values = self._prepare_portal_layout_values()
        service_ids = request.env['of.service'].search([
            ('recurrence', '=', True),
            ('state', 'not in', ('draft', 'done', 'cancel')),
            '|',
            ('partner_id', 'child_of', request.env.user.partner_id.id),
            ('address_id', 'child_of', request.env.user.partner_id.id)
        ])
        values.update({
            'contracts': service_ids,
        })
        return request.render('of_website_portal.of_website_portal_portal_my_of_contracts', values)

    @http.route(['/of_contract/<model("of.service"):contract>'], type='http', auth='user', website=True)
    def portal_of_contract(self, contract):
        values = {
            'user': request.env.user,
            'contract': contract,
        }
        return request.render('of_website_portal.of_website_portal_website_of_contract', values)

    @http.route(['/my/upload_file'], type='http', auth='user', website=True)
    def portal_my_upload_file(self, **kw):
        values = kw
        if values.get('attachment', False):
            name = values.get('attachment').filename
            partner_id = values.get('partner_id')
            attachment = values.get('attachment').read()
            request.env['ir.attachment'].sudo().create({
                'name': name,
                'datas_fname': name,
                'res_name': name,
                'type': 'binary',
                'res_model': 'res.partner',
                'res_id': partner_id,
                'datas': attachment.encode('base64'),
            })
        return request.redirect('/my/home')

    @http.route(['/my/orders/<int:order_id>'], type='http', auth="user", website=True)
    def of_portal_get_order(self, order_id=None, **kw):
        order = request.env['sale.order'].browse([order_id])
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        pdf = request.env['report'].sudo().get_pdf([order_id], 'sale.report_saleorder')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Commande.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/of_validate_sale_order'], type='http', methods=['POST'], auth="user", website=True)
    def of_validate_sale_order(self, **kw):
        if kw.get('order_id', False):
            order = request.env['sale.order'].sudo().browse([int(kw['order_id'])])
            order.action_confirm()

        return request.redirect('/my/quotes')
