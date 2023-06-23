# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import textwrap

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OFSurveyUserInputLine(models.Model):
    _name = 'of.survey.user_input.line'
    _description = "Survey User Input Line"
    _rec_name = 'user_input_id'
    _order = 'question_sequence, id'

    # survey data
    user_input_id = fields.Many2one(
        comodel_name='of.survey.user_input', string="User Input", ondelete='cascade', required=True, index=True
    )
    survey_id = fields.Many2one(related='user_input_id.survey_id', string="Survey", store=True, readonly=False)
    question_id = fields.Many2one(
        comodel_name='of.survey.question', string="Question", ondelete='cascade', required=True
    )
    page_id = fields.Many2one(related='question_id.page_id', string="Section", readonly=False)
    question_sequence = fields.Integer(string="Sequence", related='question_id.sequence', store=True)
    # answer
    skipped = fields.Boolean()
    answer_type = fields.Selection(
        selection=[
            ('text_box', "Free Text"),
            ('char_box', "Text"),
            ('date', "Date"),
            ('suggestion', "Suggestion"),
        ],
    )
    value_char_box = fields.Char(string="Text answer")
    value_date = fields.Date(string="Date answer")
    value_text_box = fields.Text(string="Free Text answer")
    suggested_answer_id = fields.Many2one(comodel_name='of.survey.question.answer', string="Suggested answer")

    @api.depends('answer_type')
    def _compute_display_name(self):
        for line in self:
            if line.answer_type == 'char_box':
                line.display_name = line.value_char_box
            elif line.answer_type == 'text_box' and line.value_text_box:
                line.display_name = textwrap.shorten(line.value_text_box, width=50, placeholder=" [...]")
            elif line.answer_type == 'date':
                line.display_name = line.value_date.strftime(
                    self.env['res.lang'].search([('code', '=', self.env.user.lang)], limit=1).date_format
                )
            elif line.answer_type == 'suggestion':
                line.display_name = line.suggested_answer_id.value

            if not line.display_name:
                line.display_name = _("Skipped")

    @api.constrains('skipped', 'answer_type')
    def _check_answer_type_skipped(self):
        for line in self:
            if line.skipped == bool(line.answer_type):
                raise ValidationError(_("A question can either be skipped or answered, not both."))

            if line.answer_type == 'suggestion':
                field_name = 'suggested_answer_id'
            elif line.answer_type:
                field_name = f'value_{line.answer_type}'
            else:  # skipped
                field_name = False

            if field_name and not line[field_name]:
                raise ValidationError(_("The answer must be in the right type"))
