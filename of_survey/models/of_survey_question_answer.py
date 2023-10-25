# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OFSurveyQuestionAnswer(models.Model):
    """A preconfigured answer for a question. This model stores values used
    for

      * simple choice, multiple choice: proposed values for the selection /
        radio;
      * matrix: row and column values;

    """

    _name = 'of.survey.question.answer'
    _rec_name = 'value'
    _order = 'sequence, id'
    _description = "Survey Label"

    # question and question related fields
    question_id = fields.Many2one(comodel_name='of.survey.question', string="Question", ondelete='cascade')
    matrix_question_id = fields.Many2one(
        comodel_name='of.survey.question', string="Question (as matrix row)", ondelete='cascade'
    )
    question_type = fields.Selection(related='question_id.question_type')
    sequence = fields.Integer(string="Label Sequence order", default=10)
    scoring_type = fields.Selection(related='question_id.scoring_type')
    # answer related fields
    value = fields.Char(string="Suggested value", translate=True, required=True)
    value_image = fields.Image(string="Image", max_width=1024, max_height=1024)
    value_image_filename = fields.Char(string="Image Filename")
    is_correct = fields.Boolean(string="Correct")
    answer_score = fields.Float(
        string="Score",
        help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer",
    )

    @api.constrains('question_id', 'matrix_question_id')
    def _check_question_not_empty(self):
        """Ensure that field question_id XOR field matrix_question_id is not null"""
        for label in self:
            if bool(label.question_id) == bool(label.matrix_question_id):
                raise ValidationError(_("A label must be attached to only one question."))
