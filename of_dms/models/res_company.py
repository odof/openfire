# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    of_virtual_file_report_ids = fields.One2many(
        comodel_name="of.dms.virtual_file_report",
        inverse_name="company_id",
        string="Virtual file reports",
    )
