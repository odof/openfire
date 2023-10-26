# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import textwrap

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


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
            ('numerical_box', "Number"),
            ('date', "Date"),
            ('datetime', "Datetime"),
            ('suggestion', "Suggestion"),
        ],
    )
    value_char_box = fields.Char(string="Text answer")
    value_numerical_box = fields.Float(string="Numerical answer")
    value_date = fields.Date(string="Date answer")
    value_datetime = fields.Datetime(string="Datetime answer")
    value_text_box = fields.Text(string="Free Text answer")
    suggested_answer_id = fields.Many2one(comodel_name='of.survey.question.answer', string="Suggested answer")
    matrix_row_id = fields.Many2one(comodel_name='of.survey.question.answer', string="Row answer")
    # scoring
    answer_score = fields.Float(string="Score")
    answer_is_correct = fields.Boolean(string="Correct")

    @api.depends('answer_type')
    def _compute_display_name(self):
        for line in self:
            if line.answer_type == 'char_box':
                line.display_name = line.value_char_box
            elif line.answer_type == 'text_box' and line.value_text_box:
                line.display_name = textwrap.shorten(line.value_text_box, width=50, placeholder=" [...]")
            elif line.answer_type == 'numerical_box':
                line.display_name = line.value_numerical_box
            elif line.answer_type == 'date':
                line.display_name = fields.Date.to_string(line.value_date)
            elif line.answer_type == 'datetime':
                line.display_name = fields.Datetime.to_string(line.value_datetime)
            elif line.answer_type == 'suggestion':
                if line.matrix_row_id:
                    line.display_name = f'{line.suggested_answer_id.value}: {line.matrix_row_id.value}'
                else:
                    line.display_name = line.suggested_answer_id.value

            if not line.display_name:
                line.display_name = _('Skipped')

    @api.constrains('skipped', 'answer_type')
    def _check_answer_type_skipped(self):
        for line in self:
            if line.skipped == bool(line.answer_type):
                raise ValidationError(_("A question can either be skipped or answered, not both."))

            # allow 0 for numerical box
            if line.answer_type == 'numerical_box' and float_is_zero(line['value_numerical_box'], precision_digits=6):
                continue
            if line.answer_type == 'suggestion':
                field_name = 'suggested_answer_id'
            elif line.answer_type:
                field_name = f'value_{line.answer_type}'
            else:  # skipped
                field_name = False

            if field_name and not line[field_name]:
                raise ValidationError(_("The answer must be in the right type"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('answer_score'):
                score_vals = self._get_answer_score_values(vals)
                vals.update(score_vals)
        return super().create(vals_list)

    def write(self, vals):
        res = True
        for line in self:
            vals_copy = {**vals}
            getter_params = {
                'user_input_id': line.user_input_id.id,
                'answer_type': line.answer_type,
                'question_id': line.question_id.id,
                **vals_copy,
            }
            if not vals_copy.get('answer_score'):
                score_vals = self._get_answer_score_values(getter_params, compute_speed_score=False)
                vals_copy |= score_vals
            res = super().write(vals_copy) and res
        return res

    @api.model
    def _get_answer_score_values(self, vals, compute_speed_score=True):
        """Get values for: answer_is_correct and associated answer_score.

        Requires vals to contain 'answer_type', 'question_id', and 'user_input_id'.
        Depending on 'answer_type' additional value of 'suggested_answer_id' may also be
        required.

        Calculates whether an answer_is_correct and its score based on 'answer_type' and
        corresponding question. Handles choice (answer_type == 'suggestion') questions
        separately from other question types. Each selected choice answer is handled as an
        individual answer.

        If score depends on the speed of the answer, it is adjusted as follows:
            - If the user answers in less than 2 seconds, they receive 100% of the possible points.
            - If user answers after that, they receive 50% of the possible points + the remaining
                50% scaled by the time limit and time taken to answer [i.e. a minimum of 50% of the
                possible points is given to all correct answers]

        Example of returned values:
            * {'answer_is_correct': False, 'answer_score': 0} (default)
            * {'answer_is_correct': True, 'answer_score': 2.0}
        """
        user_input_id = vals.get('user_input_id')
        answer_type = vals.get('answer_type')
        question_id = vals.get('question_id')
        if not question_id:
            raise ValueError(_("Computing score requires a question in arguments."))
        question = self.env['of.survey.question'].browse(int(question_id))

        # default and non-scored questions
        answer_is_correct = False
        answer_score = 0

        # record selected suggested choice answer_score (can be: pos, neg, or 0)
        if question.question_type in ['simple_choice', 'multiple_choice']:
            if answer_type == 'suggestion':
                if suggested_answer_id := vals.get('suggested_answer_id'):
                    question_answer = self.env['of.survey.question.answer'].browse(int(suggested_answer_id))
                    answer_score = question_answer.answer_score
                    answer_is_correct = question_answer.is_correct
        # for all other scored question cases, record question answer_score (can be: pos or 0)
        elif question.question_type in ['date', 'datetime', 'numerical_box']:
            answer = vals.get(f'value_{answer_type}')
            if answer_type == 'numerical_box':
                answer = float(answer)
            elif answer_type == 'date':
                answer = fields.Date.from_string(answer)
            elif answer_type == 'datetime':
                answer = fields.Datetime.from_string(answer)
            if answer and answer == question[f'answer_{answer_type}']:
                answer_is_correct = True
                answer_score = question.answer_score

        if compute_speed_score and answer_score > 0:
            user_input = self.env['of.survey.user_input'].browse(user_input_id)
            if user_input.exists() and user_input.is_session_answer and user_input.survey_id.session_speed_rating:
                max_score_delay = 2
                time_limit = question.time_limit
                now = fields.Datetime.now()
                seconds_to_answer = (now - user_input.survey_id.session_question_start_time).total_seconds()
                question_remaining_time = time_limit - seconds_to_answer
                # if answered within the max_score_delay => leave score as is
                if question_remaining_time < 0:  # if no time left
                    answer_score /= 2
                elif seconds_to_answer > max_score_delay:
                    time_limit -= max_score_delay  # we remove the max_score_delay to have all possible values
                    score_proportion = (time_limit - seconds_to_answer) / time_limit
                    answer_score = (answer_score / 2) * (1 + score_proportion)

        return {'answer_is_correct': answer_is_correct, 'answer_score': answer_score}
