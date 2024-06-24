# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBTypeBus(models.Model):
    _name = "of.esb.type.bus"
    _description = "ESB Type Bus"

    name = fields.Char()
