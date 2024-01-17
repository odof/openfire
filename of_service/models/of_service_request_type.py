# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFServiceRequestType(models.Model):
    _name = 'of.service.request.type'
    _description = "Service Type"
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    stage_ids = fields.Many2many(comodel_name='of.service.request.stage', string="Authorized Stages")
