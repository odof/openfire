# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFQuestionAnswers(models.Model):
    _name = 'of.survey.question.answers'
    _rec_name = 'question_id'
    _order = 'sequence,id'

    question_id = fields.Many2one(comodel_name='of.survey.question', string="Question")
    answers = fields.Char()
    lead_id = fields.Many2one(comodel_name='crm.lead', string="Lead")
    sequence = fields.Integer(default=10)
    is_page = fields.Boolean(related='question_id.is_page')

    def unlink(self):
        # si on supprime une ligne, il faut aussi supprimer les réponses à cette question
        questions = self.mapped('question_id')
        lines = self.env['of.survey.user_input.line'].search(
            [('survey_id', '=', self.lead_id.of_survey_id.id), ('question_id', 'in', questions.ids)]
        )
        lines and lines.unlink()
        return super().unlink()
