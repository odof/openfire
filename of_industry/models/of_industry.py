# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFIndustry(models.Model):
    "Industry"

    _name = "of.industry"
    _description = __doc__
    _order = "name"

    name = fields.Char(translate=True)
    code = fields.Char()
