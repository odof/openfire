# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBData(models.Model):
    _name = 'esb.data'

    in_data = fields.Text()
    out_data = fields.Text()
    properties = fields.Text(default='{}')
