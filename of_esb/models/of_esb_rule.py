# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import uuid

from odoo import fields, models


class ESBRule(models.Model):
    _name = "of.esb.rule"
    _description = "ESB Rule"

    name = fields.Char()
    channel_bus = fields.Char(string="Channel")
    type_bus = fields.Many2one(comodel_name="of.esb.type.bus", required=True, string="Type of bus")
    service = fields.Many2one(comodel_name="of.esb.service", required=True)
    ttype = fields.Selection(selection=[("user", "user"), ("system", "system")], string="Type", default="user")
    uuid = fields.Char(default=uuid.uuid4())

    def unlink(self):
        # we can't delete a system rule, only "user" ones
        return super(ESBRule, self.filtered(lambda r: r.ttype == "user")).unlink()
