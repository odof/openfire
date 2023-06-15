# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, http
from odoo.http import request

from odoo.addons.web.controllers.home import Home


class OFHome(Home):
    @http.route()
    def web_client(self, s_action=None, **kw):
        uid = request.session.uid
        admin_users = [SUPERUSER_ID]
        if admin_user := request.env.ref('base.user_admin', raise_if_not_found=False):
            admin_users.append(admin_user.id)
        if uid and uid not in admin_users:
            # Do not check for superuser or admin. They shouldn't be an inactives resources.
            request.cr.execute("SELECT id FROM res_users WHERE of_user_type = 'inactive' AND id = %s", (uid,))
            if request.cr.fetchall():
                return request.redirect('/inactiveuser', 303)
        return super().web_client(s_action, **kw)

    @http.route('/inactiveuser', type='http', auth="user")
    def inactive_user(self, **kw):
        if kw.get('redirect'):
            return request.redirect('/web/session/logout?redirect=/', 303)
        context = request.env['ir.http'].webclient_rendering_context()
        return request.render('of_base.inactive_user', qcontext=context)
