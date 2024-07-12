# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFDMSVirtualFileReport(models.Model):
    _name = "of.dms.virtual_file_report"
    _description = "Virtual File Report"
    _rec_name = "model_id"

    model_id = fields.Many2one(string="Model", comodel_name="ir.model")
    model_name = fields.Char(string="Model Name", related="model_id.model")
    report_id = fields.Many2one(string="Report", comodel_name="ir.actions.report")
    company_id = fields.Many2one(string="Company", comodel_name="res.company")
