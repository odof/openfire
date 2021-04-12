# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_portal.controllers.main import website_account


class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        values.update({
            'parc_installe_count': request.env.user.partner_id.of_parc_installe_count,
        })
        return values

    @http.route(['/my/of_parc_installe'], type='http', auth='user', website=True)
    def portal_my_of_of_parc_installe(self):
        values = self._prepare_portal_layout_values()
        values.update({
            'partner': request.env.user.partner_id,
            'parc_installes': request.env.user.partner_id.of_parc_installe_ids,
        })
        return request.render('of_website_portal_parc_installe.my_of_parc_installe', values)

    """@http.route(['/of_fuel_stock/<model("product.product"):fuel_stock>'], type='http', auth='user', website=True)
    def portal_of_fuel_stock(self, fuel_stock):
        values = {
            'user': request.env.user,
            'partner': request.env.user.partner_id,
            'fuel_stock': fuel_stock,
        }
        return request.render('of_website_portal_fuel_stock.of_website_portal_fuel_stock_website_of_fuel_stock', values)

    @http.route(['/of_fuel_stock/pdf/<int:picking_id>'], type='http', auth="user", website=True)
    def portal_get_of_fuel_stock(self, picking_id=None, **kw):
        pdf = request.env['report'].sudo().get_pdf([picking_id], 'stock.report_deliveryslip')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Bon_enlevement.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)"""
