# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBRule(models.Model):
    _name = 'esb.rule'

    name = fields.Char()
    channel = fields.Char(required=True)
    ttype = fields.Char(required=True, string="Type")
    service = fields.Many2one(comodel_name='esb.service', required=True)
