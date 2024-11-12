# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, http
from odoo.http import request
from odoo.service import security

from odoo.addons.web.controllers.home import Home


class OFHome(Home):
    @http.route()
    def web_client(self, s_action=None, **kw):
        uid = request.session.uid
        admin_users = [SUPERUSER_ID]
        if admin_user := request.env.ref("base.user_admin", raise_if_not_found=False):
            admin_users.append(admin_user.id)
        if uid and uid not in admin_users:
            # Do not check for superuser or admin. They shouldn't be an inactives resources.
            request.cr.execute("SELECT id FROM res_users WHERE of_user_type = 'inactive' AND id = %s", (uid,))
            if request.cr.fetchall():
                return request.redirect("/inactiveuser", 303)
        return super().web_client(s_action, **kw)

    @http.route("/inactiveuser", type="http", auth="user")
    def inactive_user(self, **kw):
        if kw.get("redirect"):
            return request.redirect("/web/session/logout?redirect=/", 303)
        context = request.env["ir.http"].webclient_rendering_context()
        return request.render("of_base.inactive_user", qcontext=context)

    @http.route("/web/become", type="http", auth="user", sitemap=False)
    def switch_to_admin(self):
        """Override the method to ensure that only `Admin` user can switch to `Superuser` and not any other user with
        Administrator access."""
        uid = request.env.user.id
        if request.env.user._is_system() and request.env.user.id == request.env.ref("base.user_admin").id:
            uid = request.session.uid = SUPERUSER_ID
            # invalidate session token cache as we've changed the uid
            request.env["res.users"].clear_caches()
            request.session.session_token = security.compute_session_token(request.session, request.env)

        return request.redirect(self._login_redirect(uid))
