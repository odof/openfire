# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SpreadsheetDashboard(models.Model):
    _inherit = "spreadsheet.dashboard"

    name = fields.Char(translate=True)
