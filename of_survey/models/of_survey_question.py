# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import contextlib
import io

import pypdfium2 as pdfium

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.osv import expression


class OFSurveyQuestion(models.Model):
    """Questions that will be asked in a survey.

    Each question can have one of more suggested answers (eg. in case of
    multi-answer checkboxes, radio buttons...).

    Technical note:

    survey.question is also the model used for the survey's pages (with the "is_page" field set to True).

    A page corresponds to a "section" in the interface, and the fact that it separates the survey in
    actual pages in the interface depends on the "questions_layout" parameter on the survey.survey model.
    Pages are also used when randomizing questions. The randomization can happen within a "page".

    Using the same model for questions and pages allows to put all the pages and questions together in a o2m field
    (see survey.survey.question_and_page_ids) on the view side and easily reorganize your survey by dragging the
    items around.

    It also removes on level of encoding by directly having 'Add a page' and 'Add a question'
    links on the tree view of questions, enabling a faster encoding.

    However, this has the downside of making the code reading a little bit more complicated.
    Efforts were made at the model level to create computed fields so that the use of these models
    still seems somewhat logical. That means:
    - A survey still has "page_ids" (question_and_page_ids filtered on is_page = True)
    - These "page_ids" still have question_ids (questions located between this page and the next)
    - These "question_ids" still have a "page_id"

    That makes the use and display of these information at view and controller levels easier to understand.
    """

    _name = "of.survey.question"
    _description = "Survey Question"
    _rec_name = "title"
    _order = "sequence,id"

    # question generic data
    title = fields.Char(required=True, translate=True)
    description = fields.Html(
        translate=True,
        sanitize=True,
        sanitize_overridable=True,
        help="Use this field to add additional explanations about your question or to illustrate it with pictures "
        "or a video",
    )
    question_placeholder = fields.Char(
        "Placeholder", translate=True, compute="_compute_question_placeholder", store=True, readonly=False
    )
    background_image = fields.Image(compute="_compute_background_image", store=True, readonly=False)
    background_image_url = fields.Char(string="Background Url", compute="_compute_background_image_url")
    survey_id = fields.Many2one(comodel_name="of.survey.survey", string="Survey", ondelete="cascade")
    sequence = fields.Integer(default=10)
    question_number = fields.Char(compute="_compute_question_number")

    # page specific
    is_page = fields.Boolean(string="Is a page?")
    question_ids = fields.One2many(
        comodel_name="of.survey.question", string="Questions", compute="_compute_question_ids"
    )
    questions_selection = fields.Selection(
        related="survey_id.questions_selection",
        readonly=True,
        help="If randomized is selected, add the number of random questions next to the section.",
    )
    # question specific
    page_id = fields.Many2one(comodel_name="of.survey.question", string="Page", compute="_compute_page_id", store=True)
    question_type = fields.Selection(
        selection=[
            ("simple_choice", "Multiple choice: only one answer"),
            ("multiple_choice", "Multiple choice: multiple answers allowed"),
            ("text_box", "Multiple Lines Text Box"),
            ("char_box", "Single Line Text Box"),
            ("date", "Date"),
            ("multi_image", "Upload Image"),
            ("form", "Form"),
            ("numerical_box", "Numerical Value"),
        ],
        compute="_compute_question_type",
        readonly=False,
        store=True,
    )
    answer_numerical_box = fields.Float("Correct numerical answer", help="Correct number answer for this question.")

    add_pictures = fields.Boolean(string="Add picture(s)")
    # -- char_box
    save_as_email = fields.Boolean(
        string="Save as user email",
        compute="_compute_save_as_email",
        readonly=False,
        store=True,
        copy=True,
        help="If checked, this option will save the user's answer as its email address.",
    )
    # -- simple choice / multiple choice
    suggested_answer_ids = fields.One2many(
        comodel_name="of.survey.question.answer",
        inverse_name="question_id",
        string="Types of answers",
        copy=True,
        help="Labels used for proposed choices: simple choice, multiple choice",
    )
    # -- form
    editable_pdf = fields.Binary(string="Editable PDF")
    background_image_pdf = fields.Binary(string="Background Image for PDF")

    time_limit = fields.Integer(string="Time limit (seconds)")
    # -- comments (simple choice, multiple choice)
    comments_allowed = fields.Boolean(string="Show Comments Field")
    comments_message = fields.Char(string="Comment Message", translate=True)
    comment_count_as_answer = fields.Boolean(string="Comment is an answer")
    # question validation
    validation_required = fields.Boolean(
        string="Validate entry", compute="_compute_validation_required", readonly=False, store=True
    )
    validation_email = fields.Boolean(string="Input must be an email")
    validation_length_min = fields.Integer(string="Minimum Text Length", default=0)
    validation_length_max = fields.Integer(string="Maximum Text Length", default=0)
    validation_min_float_value = fields.Float(string="Minimum value", default=0.0)
    validation_max_float_value = fields.Float(string="Maximum value", default=0.0)
    validation_min_date = fields.Date(string="Minimum Date")
    validation_max_date = fields.Date(string="Maximum Date")
    validation_min_datetime = fields.Datetime(string="Minimum Datetime")
    validation_max_datetime = fields.Datetime(string="Maximum Datetime")
    validation_error_msg = fields.Char(string="Validation Error message", translate=True)
    constr_mandatory = fields.Boolean(string="Mandatory Answer")
    constr_error_msg = fields.Char(string="Error message", translate=True)
    # answers
    user_input_line_ids = fields.One2many(
        comodel_name="of.survey.user_input.line",
        inverse_name="question_id",
        string="Answers",
        domain=[("skipped", "=", False)],
        groups="of_survey.group_of_survey_user",
    )
    # Default values
    default_text = fields.Text()
    default_date = fields.Date()
    # Conditional display
    is_conditional = fields.Boolean(
        string="Conditional Display",
        copy=True,
        help="""If checked, this question will be displayed only
        if the specified conditional answer have been selected in a previous question""",
    )
    conditions = fields.Char(compute="_compute_conditions")
    conditional_questions = fields.One2many(
        comodel_name="of.survey.conditional.question", inverse_name="question_id", string="Conditional questions"
    )
    conditional_domain = fields.Char(compute="_compute_conditional_domain")

    _sql_constraints = [
        ("positive_len_min", "CHECK (validation_length_min >= 0)", "A length must be positive!"),
        ("positive_len_max", "CHECK (validation_length_max >= 0)", "A length must be positive!"),
        (
            "validation_length",
            "CHECK (validation_length_min <= validation_length_max)",
            "Max length cannot be smaller than min length!",
        ),
        (
            "validation_float",
            "CHECK (validation_min_float_value <= validation_max_float_value)",
            "Max value cannot be smaller than min value!",
        ),
        (
            "validation_date",
            "CHECK (validation_min_date <= validation_max_date)",
            "Max date cannot be smaller than min date!",
        ),
        (
            "validation_datetime",
            "CHECK (validation_min_datetime <= validation_max_datetime)",
            "Max datetime cannot be smaller than min datetime!",
        ),
    ]

    # --------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # --------------------------------------------------------------------------

    @api.constrains("is_page")
    def _check_question_type_for_pages(self):
        if invalid_pages := self.filtered(lambda question: question.is_page and question.question_type):
            raise ValidationError(
                _("Question type should be empty for these pages: %s", ", ".join(invalid_pages.mapped("title")))
            )

    # --------------------------------------------------------------------------
    # COMPUTE METHODS
    # --------------------------------------------------------------------------

    @api.depends("survey_id", "survey_id.question_ids")
    def _compute_question_number(self):
        survey_map = {}
        for question in self:
            if question.survey_id:
                survey_map.setdefault(question.survey_id.id, []).append(question)

        for questions_in_survey in survey_map.values():
            survey = questions_in_survey[0].survey_id
            all_questions = survey.question_ids.filtered(lambda q: not q.is_page).sorted("sequence")
            question_index_map = {q.id: i for i, q in enumerate(all_questions, 1)}

            for q in questions_in_survey:
                if not q.is_page and q.id in question_index_map:
                    q.question_number = f"Q{question_index_map[q.id]}"
                else:
                    q.question_number = False

    @api.depends("question_type")
    def _compute_question_placeholder(self):
        for question in self:
            if (
                question.question_type in ("simple_choice", "multiple_choice") or not question.question_placeholder
            ):  # avoid CacheMiss errors
                question.question_placeholder = False

    @api.depends("is_page")
    def _compute_background_image(self):
        """Background image is only available on sections."""
        for question in self.filtered(lambda q: not q.is_page):
            question.background_image = False

    @api.depends("survey_id.access_token", "background_image", "page_id", "survey_id.background_image_url")
    def _compute_background_image_url(self):
        """How the background url is computed:
        - For a question: it depends on the related section (see below)
        - For a section:
            - if a section has a background, then we create the background URL using this section's ID
            - if not, then we fallback on the survey background url"""
        base_bg_url = "/of_survey/%s/%s/get_background_image"
        for question in self:
            if question.is_page:
                background_section_id = question.id if question.background_image else False
            else:
                background_section_id = question.page_id.id if question.page_id.background_image else False

            if background_section_id:
                question.background_image_url = base_bg_url % (question.survey_id.access_token, background_section_id)
            else:
                question.background_image_url = question.survey_id.background_image_url

    @api.depends("is_page")
    def _compute_question_type(self):
        pages = self.filtered(lambda question: question.is_page)
        pages.question_type = False
        (self - pages).filtered(lambda question: not question.question_type).question_type = "simple_choice"

    @api.depends("survey_id.question_and_page_ids.is_page", "survey_id.question_and_page_ids.sequence")
    def _compute_question_ids(self):
        """Will take all questions of the survey for which the index is higher than the index of this page
        and lower than the index of the next page."""
        for question in self:
            if question.is_page:
                next_page_index = False
                for page in question.survey_id.page_ids:
                    if page._index() > question._index():
                        next_page_index = page._index()
                        break

                question.question_ids = question.survey_id.question_ids.filtered(
                    lambda q: q._index() > question._index() and (not next_page_index or q._index() < next_page_index)
                )
            else:
                question.question_ids = self.env["of.survey.question"]

    @api.depends("survey_id.question_and_page_ids.is_page", "survey_id.question_and_page_ids.sequence")
    def _compute_page_id(self):
        """Will find the page to which this question belongs to by looking inside the corresponding survey"""
        for question in self:
            if question.is_page:
                question.page_id = None
            else:
                page = None
                for q in question.survey_id.question_and_page_ids.sorted():
                    if q == question:
                        break
                    if q.is_page:
                        page = q
                question.page_id = page

    @api.depends("question_type", "validation_email")
    def _compute_save_as_email(self):
        for question in self:
            if question.question_type != "char_box" or not question.validation_email:
                question.save_as_email = False

    @api.depends("question_type")
    def _compute_validation_required(self):
        for question in self:
            if not question.validation_required or question.question_type not in [
                "char_box",
                "date",
                "numerical_box",
            ]:
                question.validation_required = False

    @api.depends("conditional_questions")
    def _compute_conditions(self):
        for question in self:
            conditionals = question.conditional_questions.filtered(
                lambda record: record.triggering_question_id and record.answer_ids
            )
            if len(conditionals) == 0:
                conditions = ""
            else:
                conditions = _("if ")
                for line in conditionals:
                    if line.id != conditionals[0].id:
                        conditions += f" {line.operator} "
                    question_index = question.survey_id.question_ids.ids.index(line.triggering_question_id.id) + 1
                    answers_index = []
                    for answer in line.answer_ids:
                        idx = line.triggering_question_id.suggested_answer_ids.mapped("value").index(answer.value) + 1
                        answers_index.append(f"R{idx}")
                    conditions += f"Q{question_index}={','.join(answers_index)}"
            question.conditions = conditions

    @api.depends("conditional_questions")
    def _compute_conditional_domain(self):
        for question in self:
            domain = []
            for conditional in question.conditional_questions.filtered(
                lambda record: record.question_id is not False and len(record.answer_ids) > 0
            ):
                if conditional.operator == "OR":
                    domain = expression.OR(
                        [
                            domain,
                            [
                                ("question_id.id", "=", conditional.triggering_question_id.id),
                                ("suggested_answer_id.id", "in", conditional.answer_ids.ids),
                            ],
                        ]
                    )
                else:
                    domain = expression.AND(
                        [
                            domain,
                            [
                                ("question_id.id", "=", conditional.triggering_question_id.id),
                                ("suggested_answer_id.id", "in", conditional.answer_ids.ids),
                            ],
                        ]
                    )
            question.conditional_domain = domain

    def is_valid_condition(self):
        """Vérifie que la condition de la question est valide :
        - N'est pas une page
        - Le type des triggering_questions est 'simple_choice' ou 'multiple_choice'
        - Toutes les questions ont des réponses suggérées
        """
        return (
            not self.is_page
            and all(
                triggering_question.question_type in ["simple_choice", "multiple_choice"]
                and triggering_question.suggested_answer_ids
                for triggering_question in self.conditional_questions.mapped("triggering_question_id")
            )
            and all(len(answer_ids) > 0 for answer_ids in self.conditional_questions.mapped("answer_ids"))
        )

    # ------------------------------------------------------------
    # onchange method
    # ------------------------------------------------------------

    @api.onchange("editable_pdf")
    def _onchange_editable_pdf(self):
        if self.editable_pdf:
            # on convertit la première page du form en image
            pdf = pdfium.PdfDocument(base64.b64decode(self.editable_pdf))
            page = pdf[0]
            bitmap = page.render(scale=1)
            image = bitmap.to_pil()
            with io.BytesIO() as output:
                image.save(output, format="PNG")
                contents = output.getvalue()
            self.background_image_pdf = base64.b64encode(contents)
        else:
            self.background_image_pdf = False

    # ------------------------------------------------------------
    # ORM Methods
    # ------------------------------------------------------------

    def unlink(self):
        self._process_of_image_delete()
        return super().unlink()

    # ------------------------------------------------------------
    # Business Methods
    # ------------------------------------------------------------

    def _process_of_image_delete(self):
        """As we also create a `of.image` record for each image, we need to delete it as well."""
        for record in self:
            if images := record.suggested_answer_ids.mapped('value_of_image_id'):
                images.unlink()

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    def validate_question(self, answer, comment=None):
        """Validate question, depending on question type and parameters
        for simple choice, text, date and number, answer is simply the answer of the question.
        For other multiple choices questions, answer is a list of answers (the selected choices
        :
            - Simple answer : answer = 'example' or 2 or question_answer_id or 2019/10/10
            - Multiple choice : answer = [question_answer_id1, question_answer_id2, question_answer_id3]

        return dict {question.id (int): error (str)} -> empty dict if no validation error.
        """
        self.ensure_one()
        if isinstance(answer, str):
            answer = answer.strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer and self.question_type not in ["simple_choice", "multiple_choice"]:
            return {self.id: self.constr_error_msg or _("This question requires an answer.")}

        # because in choices question types, comment can count as answer
        if answer or self.question_type in ["simple_choice", "multiple_choice"]:
            if self.question_type == "char_box":
                return self._validate_char_box(answer)
            elif self.question_type == "numerical_box":
                return self._validate_numerical_box(answer)
            elif self.question_type in ["date"]:
                return self._validate_date(answer)
            elif self.question_type in ["simple_choice", "multiple_choice"]:
                return self._validate_choice(answer, comment)
        return {}

    def _validate_char_box(self, answer):
        if not tools.email_normalize(answer) and self.validation_email:
            return {self.id: _("This answer must be an email address")}

        if not (self.validation_length_min <= len(answer) <= self.validation_length_max) and self.validation_required:
            return {self.id: self.validation_error_msg or _("The answer you entered is not valid.")}
        return {}

    def _validate_numerical_box(self, answer):
        try:
            floatanswer = float(answer)
        except ValueError:
            return {self.id: _("This is not a number")}

        if self.validation_required:
            # Answer is not in the right range
            with contextlib.suppress(Exception):
                if not (self.validation_min_float_value <= floatanswer <= self.validation_max_float_value):
                    return {self.id: self.validation_error_msg or _("The answer you entered is not valid.")}
        return {}

    def _validate_date(self, answer):
        # Checks if user input is a date
        try:
            dateanswer = fields.Date.from_string(answer)
        except ValueError:
            return {self.id: _("This is not a date")}
        if self.validation_required:
            min_date = fields.Date.from_string(self.validation_min_date)
            max_date = fields.Date.from_string(self.validation_max_date)
            dateanswer = fields.Date.from_string(answer)

            if (
                (min_date and max_date and not (min_date <= dateanswer <= max_date))
                or (min_date and not min_date <= dateanswer)
                or (max_date and not dateanswer <= max_date)
            ):
                return {self.id: self.validation_error_msg or _("The answer you entered is not valid.")}
        return {}

    def _validate_choice(self, answer, comment):
        # Empty comment
        if (
            self.constr_mandatory
            and not answer
            and not (self.comments_allowed and self.comment_count_as_answer and comment)
        ):
            return {self.id: self.constr_error_msg or _("This question requires an answer.")}
        return {}

    def _index(self):
        """We would normally just use the 'sequence' field of questions BUT, if the pages and questions are
        created without ever moving records around, the sequence field can be set to 0 for all the questions.

        However, the order of the recordset is always correct so we can rely on the index method."""
        self.ensure_one()
        return list(self.survey_id.question_and_page_ids).index(self)
