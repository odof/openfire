# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBSecurity(models.Model):
    _name = "of.esb.security"
    _description = "ESB Security"

    name = fields.Char()
    ttype = fields.Selection(selection=[("none", "None"), ("password", "Password")], string="Type")
    user = fields.Char()
    password = fields.Char()
    user_id = fields.Many2one(comodel_name="res.users", string="Associated User", required=True)

    def authorize(self, args):
        if hasattr(self, f"authorize_{self.ttype}"):
            return getattr(self, f"authorize_{self.ttype}")(args)
        return False

    def authorize_none(self, args):
        return self.user_id

    def authorize_password(self, args):
        user = args.get("user")
        password = args.get("password")
        if user == self.user and password == self.password:
            return self.user_id
        return False
