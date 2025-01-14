# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveyQuestion(models.Model):
    _inherit = "of.survey.question"

    is_from_planning_booking = fields.Boolean(string="From Planning Booking?")
