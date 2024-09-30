# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class SpreadsheetDashboardGroup(models.Model):
    _inherit = "spreadsheet.dashboard.group"

    name = fields.Char(translate=True)
