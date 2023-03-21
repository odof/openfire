# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFDays(models.Model):
    _name = 'of.days'
    _description = "Week days"

    name = fields.Char(string="Day", size=16)
    abbreviation = fields.Char(string="Abbreviation", size=16)
    number = fields.Integer(string="Number", readonly=True)

    _sql_constraints = [
        ('days_number_uniq', 'unique(number)', "Two days cannot have the same number")
    ]
