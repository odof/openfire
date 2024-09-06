# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSMSSender(models.Model):
    _name = 'of.sms.sender'

    name = fields.Char()
    sender_name = fields.Char()
    model = fields.Many2one(comodel_name='ir.model', help="Empty means all model")
