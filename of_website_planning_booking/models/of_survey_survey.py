# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFSurveySurvey(models.Model):
    _inherit = "of.survey.survey"

    @api.model
    def _get_pages_or_questions(self, user_input):
        result = super()._get_pages_or_questions(user_input)
        if user_input.is_from_planning_booking:
            return result.filtered(
                lambda r: (
                    r.is_from_planning_booking
                    if not r.is_page
                    else any(question.is_from_planning_booking for question in r.question_ids)
                )
            )
        return result
