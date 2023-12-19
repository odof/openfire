# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSurveyAnswers(models.Model):
    _name = 'of.survey.answers'
    _rec_name = 'question_id'
    _order = 'sequence,id'

    question_id = fields.Many2one(comodel_name='of.survey.question', string="Question")
    answers = fields.Char()
    sequence = fields.Integer(default=10)
    is_page = fields.Boolean(related='question_id.is_page')
