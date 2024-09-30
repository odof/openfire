# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import io
import textwrap

import pypdfium2 as pdfium

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


class OFSurveyUserInputLine(models.Model):
    _name = "of.survey.user_input.line"
    _description = "Survey User Input Line"
    _rec_name = "user_input_id"
    _order = "question_sequence, id"

    # survey data
    user_input_id = fields.Many2one(
        comodel_name="of.survey.user_input", string="User Input", ondelete="cascade", required=True, index=True
    )
    survey_id = fields.Many2one(related="user_input_id.survey_id", string="Survey", store=True, readonly=False)
    question_id = fields.Many2one(
        comodel_name="of.survey.question", string="Question", ondelete="cascade", required=True
    )
    page_id = fields.Many2one(related="question_id.page_id", string="Section", readonly=False)
    question_sequence = fields.Integer(string="Sequence", related="question_id.sequence", store=True)
    # answer
    skipped = fields.Boolean()
    answer_type = fields.Selection(
        selection=[
            ("text_box", "Free Text"),
            ("char_box", "Text"),
            ("date", "Date"),
            ("suggestion", "Suggestion"),
            ("multi_image", "Upload Image"),
            ("form", "Form"),
            ("numerical_box", "Number"),
        ],
    )
    value_char_box = fields.Char(string="Text answer")
    value_numerical_box = fields.Float("Numerical answer")
    value_date = fields.Date(string="Date answer")
    value_text_box = fields.Text(string="Free Text answer")
    value_image = fields.Binary(string="Image answer")
    suggested_answer_id = fields.Many2one(comodel_name="of.survey.question.answer", string="Suggested answer")
    value_image_ids = fields.Many2many(
        comodel_name="of.image",
        help="The images corresponding to the user's upload answer, if any.",
    )
    value_form = fields.Binary(string="Form PDF")
    value_form_image = fields.Binary(string="Image")

    @api.depends("answer_type")
    def _compute_display_name(self):
        for line in self:
            if line.answer_type == "char_box":
                line.display_name = line.value_char_box
            elif line.answer_type == "text_box" and line.value_text_box:
                line.display_name = textwrap.shorten(line.value_text_box, width=50, placeholder=" [...]")
            elif line.answer_type == "numerical_box":
                line.display_name = line.value_numerical_box
            elif line.answer_type == "date":
                line.display_name = (
                    line.value_date.strftime(
                        self.env["res.lang"].search([("code", "=", self.env.user.lang)], limit=1).date_format
                    )
                    if line.value_date
                    else ""
                )
            elif line.answer_type == "suggestion":
                line.display_name = line.suggested_answer_id.value
            elif line.answer_type == "multi_image":
                line.display_name = _("{} picture(s) taken").format(len(line.value_image_ids))
            elif line.answer_type == "form":
                line.display_name = _("See files")
            if not line.display_name:
                if len(line.value_image_ids) > 0:
                    line.display_name = _("See file(s) for the answer")
                else:
                    line.display_name = _("Skipped")

    @api.constrains("skipped", "answer_type")
    def _check_answer_type_skipped(self):
        for line in self:
            if line.skipped == bool(line.answer_type):
                raise ValidationError(_("A question can either be skipped or answered, not both."))
            # allow 0 for numerical box
            if line.answer_type == "numerical_box" and float_is_zero(line["value_numerical_box"], precision_digits=6):
                continue
            if line.answer_type == "suggestion":
                field_name = "suggested_answer_id"
            elif line.answer_type == "multi_image":
                field_name = "value_image_ids"
            elif line.answer_type:
                field_name = f"value_{line.answer_type}"
            else:  # skipped
                field_name = False

            if field_name and field_name not in line._fields:
                raise ValidationError(_("The answer must be in the right type"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if form := vals.get("value_form"):
                # on convertit la première page du form en image
                pdf = pdfium.PdfDocument(base64.b64decode(form))
                pdf.init_forms()
                page = pdf[0]
                bitmap = page.render(scale=1, may_draw_forms=True)
                image = bitmap.to_pil()
                with io.BytesIO() as output:
                    image.save(output, format="PNG")
                    contents = output.getvalue()
                vals["value_form_image"] = base64.b64encode(contents)
        return super().create(vals_list)

    def write(self, vals):
        if form := vals.get("value_form"):
            # on convertit la première page du form en image
            pdf = pdfium.PdfDocument(base64.b64decode(form))
            pdf.init_forms()
            page = pdf[0]
            bitmap = page.render(scale=1, may_draw_forms=True)
            image = bitmap.to_pil()
            with io.BytesIO() as output:
                image.save(output, format="PNG")
                contents = output.getvalue()
            vals["value_form_image"] = base64.b64encode(contents)
        return super().write(vals)
