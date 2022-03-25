# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = 'res.users'

    of_is_distributor = fields.Boolean(
        u"Est un distributeur", compute='_compute_of_is_distributor', search="_search_of_is_distributor")
    of_user_ids = fields.One2many(context={'of_distributor_test': False})

    @api.depends('of_user_profile_id')
    def _compute_of_is_distributor(self):
        profile = self.env.ref('of_datastore_supplier.user_profile_distributor')
        for user in self:
            user.of_is_distributor = user.of_user_profile_id == profile

    def _search_of_is_distributor(self, operator, value):
        profile = self.env.ref('of_datastore_supplier.user_profile_distributor', raise_if_not_found=False)
        if not profile:
            return []
        if (operator == '=') == bool(value):
            return [('of_user_profile_id', '=', profile.id)]
        else:
            return ['|', ('of_user_profile_id', '=', False), ('of_user_profile_id', '!=', profile.id)]

    # Fonctions permettant de traiter les distributeurs comme des utilisateurs inactifs (many2one, etc.)
    # mais leur permettant quand-même de se connecter
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('of_distributor_test', True) and not any(item[0] == 'of_is_distributor' for item in args):
            args = [('of_is_distributor', '=', False)] + args
        return super(Users, self)._search(
            args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @classmethod
    def _of_get_login_context(cls):
        return {'of_distributor_test': False}

    @classmethod
    def _login(cls, db, login, password):
        if not password:
            return False
        user_id = False
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, cls._of_get_login_context())[cls._name]
                user = self.search([('login', '=', login)])
                if user:
                    user_id = user.id
                    user.sudo(user_id).check_credentials(password)
                    user.sudo(user_id)._update_last_login()
        except AccessDenied:
            _logger.info("Login failed for db:%s login:%s", db, login)
            user_id = False
        return user_id

    @classmethod
    def check(cls, db, uid, passwd):
        """Verifies that the given (uid, password) is authorized for the database ``db`` and
           raise an exception if it is not."""
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise AccessDenied()
        db = cls.pool.db_name
        if cls.__uid_cache[db].get(uid) == passwd:
            return
        cr = cls.pool.cursor()
        try:
            self = api.Environment(cr, uid, cls._of_get_login_context())[cls._name]
            self.check_credentials(passwd)
            cls.__uid_cache[db][uid] = passwd
        finally:
            cr.close()
