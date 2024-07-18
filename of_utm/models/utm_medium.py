# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UtmMedium(models.Model):
    _inherit = 'utm.medium'

    name = fields.Char(string="Channel Name", translate=True)
    source_ids = fields.One2many(comodel_name='utm.source', inverse_name='medium_id', string="Available sources")
