# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFServiceRequestTag(models.Model):
    _name = 'of.service.request.tag'
    _description = "Service Tag"
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    color = fields.Integer(string="Index Color")
