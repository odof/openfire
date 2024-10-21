# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFEquipmentInterventionReportTemplate(models.Model):
    _name = "of.equipment.intervention.report.template"
    _inherit = "of.planning.intervention.template.mixin"
    _description = "Equipment Intervention Report"

    name = fields.Char(compute="_compute_name", store=True, readonly=False, required=True)
    sending_report_mode = fields.Selection(
        string="Sending the equipment report",
        selection=[("attached", "Attached separately"), ("merged", "Merged with the intervention report")],
        default="merged",
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="of.equipment.intervention.report.template.line", inverse_name="template_id"
    )

    @api.depends("task_id")
    def _compute_name(self):
        for record in self:
            if not record.name:
                record.name = record.task_id.name or False
