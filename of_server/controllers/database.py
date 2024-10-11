# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import os
import re
import tempfile

import odoo
import odoo.modules.registry
from odoo import http
from odoo.http import dispatch_rpc, request
from odoo.service import db
from odoo.tools.misc import str2bool
from odoo.tools.translate import _

from odoo.addons.web.controllers.database import DBNAME_PATTERN, Database

_logger = logging.getLogger(__name__)


class OFDatabase(Database):
    @http.route("/web/database/duplicate", type="http", auth="none", methods=["POST"], csrf=False)
    def duplicate(self, master_pwd, name, new_name, neutralize_database=False, sanitize=True, drop_existing=False):
        insecure = odoo.tools.config.verify_admin_password("admin")
        if insecure and master_pwd:
            dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])
        try:
            if not re.match(DBNAME_PATTERN, new_name):
                raise Exception(
                    _("Invalid database name. Only alphanumerical characters, underscore, hyphen and dot are allowed.")
                )
            dispatch_rpc(
                "db",
                "duplicate_database",
                [
                    master_pwd,
                    name,
                    new_name,
                    str2bool(neutralize_database),
                    str2bool(sanitize),
                    str2bool(drop_existing),
                ],
            )
            if request.db == name:
                request.env.cr.close()  # duplicating a database leads to an unusable cursor
            return request.redirect("/web/database/manager")
        except Exception as e:
            _logger.exception("Database duplication error.")
            error = f"Database duplication error: {str(e) or repr(e)}"
            return self._render_template(error=error)

    @http.route("/web/database/restore", type="http", auth="none", methods=["POST"], csrf=False)
    def restore(
        self, master_pwd, backup_file, name, copy=False, neutralize_database=False, sanitize=True, drop_existing=False
    ):
        insecure = odoo.tools.config.verify_admin_password("admin")
        if insecure and master_pwd:
            dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])
        try:
            data_file = None
            db.check_super(master_pwd)
            with tempfile.NamedTemporaryFile(delete=False) as data_file:
                backup_file.save(data_file)
            db.restore_db(
                name,
                data_file.name,
                str2bool(copy),
                str2bool(neutralize_database),
                str2bool(sanitize),
                str2bool(drop_existing),
            )
            return request.redirect("/web/database/manager")
        except Exception as e:
            error = f"Database restore error: {str(e) or repr(e)}"
            return self._render_template(error=error)
        finally:
            if data_file:
                os.unlink(data_file.name)
