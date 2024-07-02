# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class OFSurveyConditionalQuestion(models.Model):
    _name = 'of.survey.conditional.question'
    _description = "Survey Conditional Question"
    _order = 'id'

    name = fields.Char(related='question_id.title')
    operator = fields.Selection(selection=[('AND', 'AND'), ('OR', 'OR')], default='AND')
    question_id = fields.Many2one(comodel_name='of.survey.question', string="Question", ondelete='cascade')
    triggering_question_id = fields.Many2one(
        comodel_name='of.survey.question', string="Triggering Question", ondelete='cascade'
    )
    answer_ids = fields.Many2many(comodel_name='of.survey.question.answer', string="Answers")
