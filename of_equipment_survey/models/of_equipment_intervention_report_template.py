# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFEquipmentInterventionReportTemplate(models.Model):
    _inherit = "of.equipment.intervention.report.template"

    survey_id = fields.Many2one(
        domain="[('survey_type', '=', 'equipment_survey')]",
    )
