# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import uuid

from odoo import fields, models

logger = logging.getLogger(__name__)


class ESBService(models.Model):
    _name = "of.esb.service"
    _description = "ESB Service"

    name = fields.Char()
    code = fields.Text()
    exec_active = fields.Boolean(string="Active", default=True)
    ttype = fields.Selection(selection=[("user", "user"), ("system", "system")], string="Type", default="user")
    uuid = fields.Char(default=uuid.uuid4())

    # -------------------------------------------------------------------------
    # ORM methods
    # -------------------------------------------------------------------------

    def unlink(self):
        # we can't delete a system service, only "user" ones
        return super(ESBService, self.filtered(lambda r: r.ttype == "user")).unlink()

    # -------------------------------------------------------------------------
    # Business methods
    # -------------------------------------------------------------------------

    def action_execute_with_delay(self, args=None):
        if args is None:
            args = {}

        if not self.exec_active:
            return {"error": "this service is not active"}

        # if there is a user_id in args.in_data, we use it to launch the action, otherwise we take the current user
        data = json.loads(args.in_data)
        if user_id := data.get("user_id"):
            user = self.env["res.users"].browse(user_id)
            return self.with_user(user).with_delay().action_execute(args)
        elif user_id := self.env.context.get("uid"):
            user = self.env["res.users"].browse(user_id)
            return self.with_user(user).with_delay().action_execute(args)
        else:
            return self.with_delay().action_execute(args)

    def action_execute(self, args=None):
        if args is None:
            args = {}
        if self.code and self.exec_active:
            exec(self.code, {"args": args, "self": self, "logger": logger, "json": json})  # nosec B102
            return {field: args[field] for field in args._fields}
        elif not self.exec_active:
            return {"error": "this service is not active"}
        else:
            return {"error": "Code is empty"}

    def get_data(self, args):
        in_data = json.loads(args.in_data)
        if ttype := in_data.get("type"):
            if hasattr(self, f"get_data_{ttype}"):
                return getattr(self, f"get_data_{ttype}")(args)
        return []

    def set_data(self, args):
        in_data = json.loads(args.in_data)
        if ttype := in_data.get("type"):
            if hasattr(self, f"set_data_{ttype}"):
                return getattr(self, f"set_data_{ttype}")(args)
        return []

    def preview(self, connection, data):
        ttype = connection.ttype
        if hasattr(self, f"preview_{ttype}"):
            return getattr(self, f"preview_{ttype}")(connection, data)
        return "Aucune preview"
