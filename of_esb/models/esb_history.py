# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBHistory(models.Model):
    _name = 'esb.history'

    service = fields.Many2one(comodel_name='esb.service')
    bus = fields.Many2one(comodel_name='esb.bus')
    date = fields.Datetime(default=fields.Datetime.now())
    job = fields.Many2one(comodel_name='queue.job')
