# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBData(models.Model):
    _name = "of.esb.data"
    _description = "ESB Data"

    in_data = fields.Text()
    out_data = fields.Text()
    properties = fields.Text(default="{}")
