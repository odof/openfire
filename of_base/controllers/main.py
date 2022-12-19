# -*- coding: utf-8 -*-

import werkzeug.utils

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.addons.web.controllers.main import Home


class OFHome(Home):

    @http.route()
    def web_client(self, s_action=None, **kw):
        uid = request.session.uid
        if uid and uid != SUPERUSER_ID:
            # Do not check for admin. Admin shouldn't be an inactive resource.
            request.cr.execute("SELECT id FROM res_users WHERE of_user_type = 'inactive' AND id = %s", (uid, ))
            res = request.cr.fetchall()
            if res:
                return werkzeug.utils.redirect('/inactiveuser', 303)
        response = super(OFHome, self).web_client(s_action, **kw)
        return response

    @http.route('/inactiveuser', type='http', auth="user")
    def inactive_user(self, **kw):
        if kw.get('redirect'):
            return werkzeug.utils.redirect('/web/session/logout?redirect=/', 303)
        context = request.env['ir.http'].webclient_rendering_context()
        return request.render('of_base.inactive_user', qcontext=context)
