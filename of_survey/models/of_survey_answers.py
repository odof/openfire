# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command, _, fields, models


class OFSurveyAnswers(models.Model):
    _name = 'of.survey.answers'
    _description = "Survey Answers"
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
    answers_images_ids = fields.One2many(
        comodel_name='of.survey.answers.images',
        inverse_name='question_id',
        string="Answers and Images",
        compute="_compute_answers_images_ids",
    )

    def _compute_image_ids(self):
        for answer in self:
            # on va chercher les images qui sont associées à la question dans le user_input
            user_input_lines = answer.user_input.user_input_line_ids.filtered(
                lambda record: record.question_id == answer.question_id
            )
            answer.image_ids = user_input_lines.mapped('value_image_ids')

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

    def _compute_answers_images_ids(self):
        for answer in self:
            if user_input_lines := answer.user_input.user_input_line_ids.filtered(
                lambda record: record.question_id == answer.question_id and not record.skipped
            ):
                values = []
                for line in user_input_lines:
                    if line.answer_type == "text_box":
                        answer_value = line.value_text_box
                    else:
                        answer_value = line.display_name

                    if line.suggested_answer_id:
                        image = line.suggested_answer_id.value_image
                    else:
                        image = False

                    values.append(
                        Command.create({'question_id': answer.question_id, 'answer': answer_value, 'image': image})
                    )
                answer.answers_images_ids = values
            else:
                answer.answers_images_ids = False
