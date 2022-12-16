# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class OFMonths(models.Model):
    _name = 'of.months'
    _description = "Months of the year"

    name = fields.Char(string="Month", size=16)
    abbreviation = fields.Char(string="Abbreviation", size=16)
    number = fields.Integer(string="Number", readonly=True)

    _sql_constraints = [
        ('months_number_uniq', 'unique(number)', "Two months cannot have the same number")
    ]
