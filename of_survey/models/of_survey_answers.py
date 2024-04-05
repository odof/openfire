# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, fields, models


class OFSurveyAnswers(models.Model):
    _name = 'of.survey.answers'
    _rec_name = 'question_id'
    _order = 'sequence,id'

    question_id = fields.Many2one(comodel_name='of.survey.question', string="Question")
    question_type = fields.Selection(related='question_id.question_type')
    answers = fields.Char()
    sequence = fields.Integer(default=10)
    is_page = fields.Boolean(related='question_id.is_page')
    user_input = fields.Many2one(comodel_name='of.survey.user_input')
    image_ids = fields.Many2many(comodel_name='of.image', compute='_compute_image_ids', string="Images")
    form = fields.Binary(string="Form PDF", compute='_compute_form')
    form_filename = fields.Char(string="Filename", compute='_compute_form')

    def _compute_image_ids(self):
        for answer in self:
            # on va chercher les images qui sont associées à la question dans le user_input
            user_input_lines = answer.user_input.user_input_line_ids.filtered(
                lambda record: record.question_id == answer.question_id
            )
            images = self.env['of.image']
            for line in user_input_lines:
                images += line.value_image_ids
            answer.image_ids = images

    def _compute_form(self):
        for answer in self:
            if user_input_lines := answer.user_input.user_input_line_ids.filtered(
                lambda record: record.question_id == answer.question_id
            ):
                answer.form = user_input_lines[0].value_form
                answer.form_filename = _("Form-%(answer_id)s.pdf", answer_id=answer.id)
            else:
                answer.form = False
                answer.form_filename = False
