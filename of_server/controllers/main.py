# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import os
import re
import tempfile

from odoo import http
from odoo.addons.web.controllers.main import Database, DBNAME_PATTERN
from odoo.http import dispatch_rpc
from odoo.service import db
from odoo.tools.misc import str2bool
from odoo.tools.translate import _


class DatabaseController(Database):

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False)
    def duplicate(self, master_pwd, name, new_name, sanitize=True, drop_existing=False):
        try:
            if not re.match(DBNAME_PATTERN, new_name):
                raise Exception(
                    _('Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.'))
            dispatch_rpc(
                'db', 'duplicate_database', [master_pwd, name, new_name, str2bool(sanitize), str2bool(drop_existing)])
            return http.local_redirect('/web/database/manager')
        except Exception, e:
            error = "Database duplication error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/restore', type='http', auth="none", methods=['POST'], csrf=False)
    def restore(self, master_pwd, backup_file, name, copy=False, sanitize=True, drop_existing=False):
        try:
            data_file = None
            db.check_super(master_pwd)
            with tempfile.NamedTemporaryFile(delete=False) as data_file:
                backup_file.save(data_file)
            db.restore_db(name, data_file.name, str2bool(copy), str2bool(sanitize), str2bool(drop_existing))
            return http.local_redirect('/web/database/manager')
        except Exception, e:
            error = "Database restore error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)
        finally:
            if data_file:
                os.unlink(data_file.name)
