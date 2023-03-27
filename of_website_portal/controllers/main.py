# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import http, tools, fields
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.addons.website_portal.controllers.main import website_account
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.of_utils.models.of_utils import format_date
from dateutil.relativedelta import relativedelta
import datetime

class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        recurrent_ids = request.env['of.service'].search([
            ('recurrence', '=', True),
            ('state', 'not in', ('draft', 'done', 'cancel')),
            '|',
            ('partner_id', 'child_of', request.env.user.partner_id.id),
            ('address_id', 'child_of', request.env.user.partner_id.id)
        ])
        service_ids = request.env['of.service'].search([
            '|',
            ('partner_id', 'child_of', request.env.user.partner_id.id),
            ('address_id', 'child_of', request.env.user.partner_id.id)
        ])
        delivery_ids = request.env['stock.picking'].search([
            ('state', 'not in', ('draft', 'cancel')),
            ('partner_id', 'child_of', request.env.user.partner_id.id)
        ])
        rdv_ids = request.env['of.planning.intervention'].search([
            ('state', 'not in', ['cancel', 'postponed']),
            '|',
            ('partner_id', 'child_of', request.env.user.partner_id.id),
            ('address_id', 'child_of', request.env.user.partner_id.id)
        ])
        values.update({
            'recurrent_count': len(recurrent_ids),
            'service_count': len(service_ids),
            'delivery_count': len(delivery_ids),
            'rdv_count': len(rdv_ids),
            'tabs': request.env.user.of_tab_ids.mapped('code'),
        })
        return values

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def account(self, **kw):
        if kw.get('canceled_rdv_id'):
            rdv = request.env['of.planning.intervention'].search([('id', '=', int(kw.get('canceled_rdv_id')))]).sudo()
            rdv.button_cancel()
            # Envoyer l'email de confirmation
            mail_template = request.env['ir.model.data'].sudo().get_object(
                'of_website_portal', 'of_website_portal_rdv_cancellation_mail_template')
            mail_id = mail_template.send_mail(rdv.id)
            mail = request.env['mail.mail'].sudo().browse(mail_id)
            mail.send()
        return super(WebsiteAccount, self).account(**kw)

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

    @http.route(['/my/services'], type='http', auth='user', website=True)
    def portal_my_services(self):
        values = self._prepare_portal_layout_values()
        service_ids = request.env['of.service'].search([
            '|',
            ('partner_id', 'child_of', request.env.user.partner_id.id),
            ('address_id', 'child_of', request.env.user.partner_id.id)
        ])
        values.update({
            'services': service_ids,
        })
        return request.render('of_website_portal.of_website_portal_portal_my_services', values)

    @http.route(['/my/services/pdf/<int:service_id>'], type='http', auth="user", website=True)
    def portal_get_service(self, service_id=None, **kw):
        service = request.env['of.service'].browse([service_id])
        try:
            service.check_access_rights('read')
            service.check_access_rule('read')
        except AccessError:
            return request.render("website.403")

        pdf = request.env['report'].sudo().get_pdf([service_id], 'of_service.report_demande_intervention')
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=Demande_intervention.pdf;')
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/my/documents'], type='http', auth='user', website=True)
    def portal_my_documents(self):
        values = self._prepare_portal_layout_values()
        document_ids = request.env['muk_dms.file'].search([
            ('of_attachment_partner_id', 'child_of', request.env.user.partner_id.id)
        ])
        values.update({
            'documents': document_ids,
        })
        return request.render('of_website_portal.of_website_portal_portal_my_documents', values)

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

    @http.route(['/my/rdvs'], type='http', auth='user', website=True)
    def of_portal_get_rdvs(self, **kw):
        values = self._prepare_portal_layout_values()
        rdv_ids = request.env['of.planning.intervention'].search([
            ('state', 'not in', ['cancel', 'postponed']),
            '|',
            ('partner_id', 'child_of', request.env.user.partner_id.id),
            ('address_id', 'child_of', request.env.user.partner_id.id)
        ])
        values.update({
            'rdvs': rdv_ids,
        })
        return request.render('of_website_portal.of_website_portal_portal_my_rdvs', values)


    @http.route(['/rdv/<model("of.planning.intervention"):rdv>'], type='http', auth='user', website=True)
    def of_portal_rdv(self, rdv=None, **kw):
        values = {
            'user': request.env.user,
            'rdv': rdv,
        }
        return request.render('of_website_portal.of_website_portal_website_rdv', values)

    @http.route(['/rdv/cancel'], type='http', auth='user', website=True)
    def of_portal_cancel_rdv(self, rdv_id, **kw):
        rdv = request.env['of.planning.intervention'].browse(int(rdv_id))
        try:
            rdv.check_access_rights('read')
            rdv.check_access_rule('read')
        except AccessError:
            return request.render('website.403')
        values = {
            'rdv': rdv,
        }
        return request.render('of_website_portal.of_website_portal_website_rdv_cancel', values)


class SignupVerifyEmail(AuthSignupHome):

    @http.route()
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        # Email verification
        email_address = http.request.params.get('login')
        if email_address and not tools.single_email_re.match(email_address):
            qcontext["error"] = u"Veuillez renseigner un courriel valide."
            return request.render('auth_signup.signup', qcontext)

        return super(SignupVerifyEmail, self).web_auth_signup(*args, **kw)
