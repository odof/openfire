# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    survey_id = fields.Many2one(comodel_name='of.survey.survey', string="Survey")
    question_ids = fields.One2many(
        comodel_name='of.survey.question', related='survey_id.question_and_page_ids', string="Questions", readonly=True
    )
    sheet_survey = fields.Boolean(string="SURVEY (sheet)")
    report_survey = fields.Boolean(string="SURVEY (report)")
