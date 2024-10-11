# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFMonths(models.Model):
    _name = "of.months"
    _description = "Months of the year"

    name = fields.Char(string="Month", size=16)
    abbreviation = fields.Char(size=16)
    number = fields.Integer(readonly=True)

    _sql_constraints = [("months_number_uniq", "unique(number)", "Two months cannot have the same number")]
