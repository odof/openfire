# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveyUserInput(models.Model):
    _inherit = "of.survey.user_input"

    is_from_planning_booking = fields.Boolean(string="From Planning Booking?")

    def _get_inactive_conditional_questions(self):
        inactive_questions = super()._get_inactive_conditional_questions()
        if self.is_from_planning_booking:
            inactive_questions |= self.survey_id.question_ids.filtered(lambda q: not q.is_from_planning_booking)
        return inactive_questions
