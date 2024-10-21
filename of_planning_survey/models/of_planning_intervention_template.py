# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = "of.planning.intervention.template"

    survey_id = fields.Many2one(
        domain="[('survey_type', '=', 'intervention_survey')]",
    )
    sheet_survey = fields.Boolean(
        string="SURVEY (sheet)", help="Adds the survey and answers to questions to the PDF document."
    )
