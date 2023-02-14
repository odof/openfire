# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UtmSource(models.Model):
    _inherit = 'utm.source'
    _order = 'sequence'

    name = fields.Char(string="Origin Name")
    active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=10)
    medium_id = fields.Many2one(comodel_name='utm.medium', string="Associated channel")
