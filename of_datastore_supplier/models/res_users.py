# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import contextlib
import logging

import pytz

from odoo import SUPERUSER_ID, api, fields, models, tools
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = "res.users"

    of_is_distributor = fields.Boolean(
        string="Is a distributor", compute="_compute_of_is_distributor", search="_search_of_is_distributor"
    )
    of_user_ids = fields.One2many(context={"of_distributor_test": False})

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends("of_user_profile_id")
    def _compute_of_is_distributor(self):
        profile = self.env.ref("of_datastore_supplier.user_profile_distributor")
        for user in self:
            user.of_is_distributor = user.of_user_profile_id == profile

    def _search_of_is_distributor(self, operator, value):
        if profile := self.env.ref(
            "of_datastore_supplier.user_profile_distributor",
            raise_if_not_found=False,
        ):
            return (
                [("of_user_profile_id", "=", profile.id)]
                if (operator == "=") == bool(value)
                else [
                    "|",
                    ("of_user_profile_id", "=", False),
                    ("of_user_profile_id", "!=", profile.id),
                ]
            )
        else:
            return []

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.context.get("of_distributor_test", True) and all(item[0] != "of_is_distributor" for item in args):
            args = [("of_is_distributor", "=", False)] + args
        return super()._search(
            args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid
        )

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    @api.model
    def of_create_new_distributor(self, login, password, name):
        """
        This function creates/updates a user based on the identifier provided.
        Its purpose is to be called in xmlrpc to dynamically populate the supplier database from our
        management database.
        """
        if user := self.with_context(of_distributor_test=False, active_test=False).search([("login", "=", login)]):
            # If User exists, update password and name if needed
            vals = {}
            if not self._crypt_context().verify(password, user.password):
                vals["password"] = password
            if name != user.name:
                vals["name"] = name
            if vals:
                user.write(vals)
        else:
            profile = self.env.ref("of_datastore_supplier.user_profile_distributor", raise_if_not_found=False)
            self.create(
                {
                    "login": login,
                    "name": name,
                    "of_user_profile_id": profile.id,
                    "password": password,
                }
            )
        return True

    @classmethod
    def _of_get_login_context(cls):
        return {"of_distributor_test": False}

    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        """Copied from `odoo.addons.base.models.res_users.ResUsers._login()` and modified to add a login context
        allowing to authenticate distributors even if they are inactive.
        """
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, cls._of_get_login_context())[cls._name]
                with self._assert_can_auth(user=login):
                    user = self.search(self._get_login_domain(login), order=self._get_login_order(), limit=1)
                    if not user:
                        raise AccessDenied()
                    user = user.with_user(user)
                    user._check_credentials(password, user_agent_env)
                    tz = request.httprequest.cookies.get("tz") if request else None
                    if tz in pytz.all_timezones and (not user.tz or not user.login_date):
                        # first login or missing tz -> set tz to browser tz
                        user.tz = tz
                    user._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for db:%s login:%s from %s", db, login, ip)
            raise

        _logger.info("Login successful for db:%s login:%s from %s", db, login, ip)

        return user.id

    @classmethod
    @tools.ormcache("uid", "passwd")
    def check(cls, db, uid, passwd):
        """Copied from `odoo.addons.base.models.res_users.ResUsers.check()` and modified to add a login context

        Verifies that the given (uid, password) is authorized for the database ``db`` and
        raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise AccessDenied()

        with contextlib.closing(cls.pool.cursor()) as cr:
            self = api.Environment(cr, uid, cls._of_get_login_context())[cls._name]
            with self._assert_can_auth(user=uid):
                if not self.env.user.active:
                    raise AccessDenied()
                self._check_credentials(passwd, {"interactive": False})
