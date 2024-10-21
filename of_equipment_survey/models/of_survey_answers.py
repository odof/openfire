# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveyAnswers(models.Model):
    _inherit = "of.survey.answers"

    equipment_link_id = fields.Many2one(comodel_name="of.calendar.event.equipment.link", string="Equipment Link")

    def unlink(self):
        # if a line is deleted, we must also delete the answers to this question
        questions = self.mapped("question_id")
        lines = self.env["of.survey.user_input.line"].search(
            [("survey_id", "=", self.equipment_link_id.survey_id.id), ("question_id", "in", questions.ids)]
        )
        lines and lines.unlink()
        return super().unlink()
