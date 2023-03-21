# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.tools import email_re
from odoo.addons.of_base.models.partner import convert_phone_number

from odoo.addons.website.controllers.main import Website
from odoo.addons.web.controllers.main import Home
from odoo.addons.auth_signup.controllers.main import AuthSignupHome


class OFWebsite(Website):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        return request.render('of_lab.lab_homepage')


class OFHome(Home):

    @http.route(website=True, auth="public")
    def web_login(self, redirect=None, *args, **kw):
        response = super(OFHome, self).web_login(redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            uid = request.uid
            if uid and uid != SUPERUSER_ID:
                # Do not check for admin. Admin shouldn't be lab user.
                request.cr.execute("SELECT id FROM res_users WHERE of_portal = True AND id = %s", (uid,))
                res = request.cr.fetchall()
                if res:
                    return http.redirect_with_hash('/lab')
        return response


class OFAuthSignupHome(AuthSignupHome):

    @http.route()
    def web_auth_signup(self, *args, **kw):
        response = super(OFAuthSignupHome, self).web_auth_signup(*args, **kw)
        if request.params.get('login_success'):
            uid = request.uid
            if uid and uid != SUPERUSER_ID:
                # Do not check for admin. Admin shouldn't be lab user.
                request.cr.execute("SELECT id FROM res_users WHERE of_portal = True AND id = %s", (uid,))
                res = request.cr.fetchall()
                if res:
                    return http.redirect_with_hash('/lab')
        return response


class OFWebsiteLab(http.Controller):

    @http.route(['/lab'], type='http', auth='user', website=True)
    def lab(self, **post):
        return request.render('of_lab.lab')

    @http.route(['/lab/mobile_app_modal'], type='json', auth='user', website=True)
    def mobile_app_modal(self, **kw):
        return request.env['ir.ui.view'].render_template('of_lab.lab_mobile_app_modal')

    @http.route(['/lab/yousign_modal'], type='json', auth='user', website=True)
    def yousign_modal(self, **kw):
        uid = request.env.uid
        partner = request.env['res.users'].browse(uid).partner_id
        return request.env['ir.ui.view'].render_template(
            'of_lab.lab_yousign_modal', {'email': partner.email, 'mobile': partner.mobile})

    @http.route(['/lab/yousign_modal/process'], methods=['POST'], type='json', auth='user')
    def yousign_modal_process(self, **kw):
        errors = []
        email = kw.get('email', '')
        mobile = kw.get('mobile', '')
        if not email:
            errors.append(u"Veuillez renseigner un courriel.")
        if not mobile:
            errors.append(u"Veuillez renseigner un numéro de mobile.")

        if errors:
            return False, True, '<br/>'.join(errors)
        else:
            # Check email
            if not email_re.match(email):
                errors.append(u"Veuillez renseigner un courriel valide.")
            # Check mobile
            if not bool(convert_phone_number(mobile, 'FR', strict=True)):
                errors.append(u"Veuillez renseigner un numéro de mobile valide.")

            if errors:
                return False, True, '<br/>'.join(errors)
            else:
                uid = request.env.uid
                request.env['res.users'].sudo().browse(uid).partner_id.write({
                    'email': kw.get('email', ''),
                    'mobile': kw.get('mobile', '')
                })

                return True, False, False
