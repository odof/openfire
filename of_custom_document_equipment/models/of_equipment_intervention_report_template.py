# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = "of.equipment.intervention.report.template"

    # INTERVENTION REPORT (IR)
    # Note: Other fields are already defined in the mixin.
    report_custom_document_ids = fields.Many2many(
        comodel_name="of.custom.document",
        relation="report_equipment_intervention_custom_document",
        string="Joined documents (IR)",
        help="Adds customized documents selected in the equipment as an appendix to the PDF document.",
    )
