# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_virtual_file_report_ids = fields.One2many(related="company_id.of_virtual_file_report_ids", readonly=False)
