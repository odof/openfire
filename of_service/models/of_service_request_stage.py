# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFServiceRequestStage(models.Model):
    _name = "of.service.request.stage"
    _description = "Service Stage"
    _order = "sequence"

    name = fields.Char()
    sequence = fields.Integer()
    type_ids = fields.Many2many(comodel_name="of.service.request.type", string="Authorized types")
