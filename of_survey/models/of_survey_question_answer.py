# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSurveyQuestionAnswer(models.Model):
    """A preconfigured answer for a question. This model stores values used
    for

      * simple choice, multiple choice: proposed values for the selection /
        radio;

    """

    _name = "of.survey.question.answer"
    _rec_name = "value"
    _order = "sequence, id"
    _description = "Survey Label"

    # question and question related fields
    question_id = fields.Many2one(comodel_name="of.survey.question", string="Question", ondelete="cascade")

    question_type = fields.Selection(related="question_id.question_type")
    sequence = fields.Integer(string="Label Sequence order", default=10)
    # answer related fields
    value = fields.Char(string="Suggested value", translate=True, required=True)
    value_image = fields.Image(string="Image", max_width=1024, max_height=1024)
    value_image_filename = fields.Char(string="Image Filename")
    is_correct = fields.Boolean(string="Correct")
    is_default = fields.Boolean(string="Is default")
    value_of_image_id = fields.Many2one(comodel_name="of.image", string="Value Image")

    @api.model_create_multi
    def create(self, list_vals):
        for vals in list_vals:
            if "value_image" in vals:
                vals["value_of_image_id"] = (
                    self.env["of.image"]
                    .create({"name": vals.get("value_image_filename"), "image_1920": vals.get("value_image")})
                    .id
                )
        return super().create(list_vals)

    def write(self, vals):
        if "value_image" in vals:
            for record in self:
                if record.value_of_image_id:
                    record.value_of_image_id.image_1920 = vals.get("value_image")
            vals["value_of_image_id"] = (
                self.env["of.image"]
                .create({"name": vals.get("value_image_filename"), "image_1920": vals.get("value_image")})
                .id
            )
        return super().write(vals)

    def unlink(self):
        of_images = self.mapped("value_of_image_id")
        res = super().unlink()
        of_images.unlink()
        return res

    def action_button_check_suggested_answer_ids(self):
        if answer_id := self.env.context.get("active_answer"):
            if self.question_type == "simple_choice":
                for answer in self.question_id.suggested_answer_ids:
                    answer.is_default = answer.id == answer_id
            else:
                self.is_default = True

    def action_button_uncheck_suggested_answer_ids(self):
        if self.env.context.get("active_answer"):
            self.is_default = False
