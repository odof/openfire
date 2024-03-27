# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class OFSurveyAnswers(models.Model):
    _name = 'of.survey.answers'
    _rec_name = 'question_id'
    _order = 'sequence,id'

    question_id = fields.Many2one(comodel_name='of.survey.question', string="Question")
    question_type = fields.Selection(related='question_id.question_type')
    answers = fields.Char()
    sequence = fields.Integer(default=10)
    is_page = fields.Boolean(related='question_id.is_page')
    user_input = fields.Many2one(comodel_name='of.survey.user_input', string="User Input")
    images = fields.Many2many(comodel_name='ir.attachment', compute='_compute_images', string="Images")

    def _compute_images(self):
        for answers in self:
            # on va chercher les images qui sont associées à la question dans le user_input
            user_input_lines = answers.user_input.user_input_line_ids.filtered(
                lambda record: record.question_id == answers.question_id
            )
            images = self.env['ir.attachment']
            for line in user_input_lines:
                images += line.value_file_data_ids
            answers.images = images
