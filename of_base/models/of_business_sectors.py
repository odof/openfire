# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFBusinessSectors(models.Model):
    _name = "of.business.sectors"
    _description = "Business sectors for database qualification"

    name = fields.Char(translate=True)
