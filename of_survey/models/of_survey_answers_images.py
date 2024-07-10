# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveyAnswersImages(models.Model):
    _name = 'of.survey.answers.images'
    _description = "Survey Answers Images"
    _rec_name = 'answer'

    answer = fields.Char()
    image = fields.Binary()
    question_id = fields.Many2one(comodel_name='of.survey.question', string="Question")
