# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models


class OFCalendarEventEquipmentLink(models.Model):
    _name = "of.calendar.event.equipment.link"
    _inherit = ["of.calendar.event.equipment.link", "of.equipment.report.mixin"]

    survey_id = fields.Many2one(
        comodel_name="of.survey.survey",
        string="Survey",
        domain=[("survey_type", "=", "equipment_survey")],
        help="Select the survey to be answered as part of the equipment intervention.",
    )
    survey_user_input_id = fields.Many2one(
        comodel_name="of.survey.user_input",
        string="Survey User Input",
        compute="_compute_survey_user_input_id",
        store=True,
        readonly=False,
    )
    survey_user_input_line_ids = fields.One2many(
        comodel_name="of.survey.user_input.line",
        related="survey_user_input_id.user_input_line_ids",
        string="Survey User Input Line",
    )
    question_ids = fields.One2many(
        comodel_name="of.survey.question", related="survey_id.question_and_page_ids", string="Questions"
    )
    answers_ids = fields.One2many(
        comodel_name="of.survey.answers",
        inverse_name="equipment_link_id",
        string="Question and Answers",
        compute="_compute_question_answers_ids",
        store=True,
        readonly=False,
    )

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("survey_id")
    def _compute_survey_user_input_id(self):
        for link in self:
            if link.survey_id:
                link.survey_user_input_id = link.survey_id._create_answer(user=self.env.user, email=self.env.user.email)
                link.survey_user_input_id.res_model = link._name
                link.survey_user_input_id.res_id = link._origin.id
                link.survey_user_input_id.redirect_action_id = self.env.ref("calendar.action_calendar_event").id
                link.survey_user_input_id.menu_id = self.env.ref("of_planning.menu_of_planning_main").id

    @api.depends("survey_user_input_line_ids", "question_ids")
    def _compute_question_answers_ids(self):
        for link in self:
            link.answers_ids = False
            question_answers_ids = []

            for question in link.question_ids:
                # we find out if the answer is the same, if so, we do nothing, if not, we create it.
                question_answers = link.answers_ids.filtered(lambda r: r.question_id.id == question.id)
                if question.is_page:
                    # we are on a section
                    answers = ""
                else:
                    input_lines = link.survey_user_input_line_ids.filtered(lambda r: r.question_id.id == question.id)
                    # When we have a multiple choice question with "comment allowed" option, we want to skip the
                    # skipped answers if there is at least one answer given by the user to avoid having something like
                    # `"Ignored, Answered text"` in the answers field.
                    answer_lines = [
                        line.display_name
                        for line in input_lines
                        if len(input_lines.filtered(lambda r: r.question_id.id == line.question_id.id)) <= 1
                        or not line.skipped
                        or line.question_id.question_type != "multiple_choice"
                    ]
                    answers = ", ".join(answer_lines)

                if len(question_answers) == 1:
                    if question_answers.answers != answers:
                        question_answers_ids.append(
                            Command.update(
                                question_answers.id,
                                {"answers": answers, "user_input": link.survey_user_input_id.id},
                            )
                        )
                else:
                    question_answers_value = {
                        "question_id": question.id,
                        "answers": answers,
                        "sequence": question.sequence,
                        "user_input": link.survey_user_input_id.id,
                    }
                    question_answers_ids.append(Command.create(question_answers_value))
            link.answers_ids = question_answers_ids

    # --------------------------------------------------------------------------
    # Onchange methods
    # --------------------------------------------------------------------------

    @api.onchange("survey_id")
    def _onchange_survey_id(self):
        """When the survey is changed we remove the answers and create a new user input.

        We need to do that stuff in the onchange too because the survey can be changed in the view and never opened from
        the button `action_button_open_survey`.

        That case should happen when survey is called from GraphQL API. # TODO: move me in a graphql module ?
        """
        if self.survey_id:
            self.answers_ids = False
            self.survey_user_input_id = self.survey_id._create_answer(user=self.env.user, email=self.env.user.email)
            self.survey_user_input_id.res_model = self._name
            self.survey_user_input_id.res_id = self._origin.id
            self.survey_user_input_id.redirect_action_id = self.env.ref(
                "of_equipment.of_calendar_event_equipment_link_form_action"
            ).id
            self.survey_user_input_id.menu_id = self.env.ref("of_planning.menu_of_planning_main").id

    # --------------------------------------------------------------------------
    # Actions methods
    # --------------------------------------------------------------------------

    def action_button_back_to_event(self):
        """Return an action to open the event form view.

        As the survey send us back to equipment link form without any breadcrumb that contains the event, we need a way
        to go back to it.
        """
        self.ensure_one()
        action_url = (
            f"/web#id={self.event_id.id}&model={self.event_id._name}&view_type=form&"
            f'action={self.env.ref("of_planning.action_calendar_event").id}&'
            f'menu_id={self.env.ref("of_planning.menu_of_planning_main").id}'
        )
        return {
            "type": "ir.actions.act_url",
            "name": _("Back to Event"),
            "target": "self",
            "url": action_url,
        }

    def action_button_open_survey(self):
        """
        Open the survey associated with the equipment link.

        We have to create a new user input to allow the user to answer the survey.
        We need to create a new user input each time we open the survey because we need to keep track of the answers
        given by the user.

        Returns:
            dict: An action dictionary to open the survey URL.
        """
        self.ensure_one()
        # cleaning up old data
        self.env["of.survey.user_input"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self._origin.id),
            ]
        ).unlink()
        self.survey_user_input_id = self.survey_id._create_answer(user=self.env.user, email=self.env.user.email)
        self.survey_user_input_id.res_model = self._name
        self.survey_user_input_id.res_id = self._origin.id
        self.survey_user_input_id.redirect_action_id = self.env.ref(
            "of_equipment.of_calendar_event_equipment_link_form_action"
        ).id
        self.survey_user_input_id.menu_id = self.env.ref("of_planning.menu_of_planning_main").id

        url = f"/of_survey/{self.survey_id.access_token}/{self.survey_user_input_id.access_token}"
        return {
            "type": "ir.actions.act_url",
            "name": _("Start Survey"),
            "target": "self",
            "url": url,
        }

    def action_button_edit_survey(self):
        self.survey_user_input_id._mark_in_progress()
        self.survey_user_input_id.last_displayed_page_id = 0
        url = f"/of_survey/{self.survey_id.access_token}/{self.survey_user_input_id.access_token}"
        return {
            "type": "ir.actions.act_url",
            "name": _("Edit Survey"),
            "target": "self",
            "url": url,
        }

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _add_missing_calendar_equipment_link_fields(self, vals_list):
        super()._add_missing_calendar_equipment_link_fields(vals_list)
        for vals in vals_list:
            if not vals.get("survey_id") and vals.get("equipment_report_tmpl_id"):
                template = self.env["of.equipment.intervention.report.template"].browse(
                    vals["equipment_report_tmpl_id"]
                )
                vals["survey_id"] = template.survey_id.id

    # --------------------------------------------------------------------------
    # Reports methods
    # --------------------------------------------------------------------------

    @property
    def _answer_field_name(self):
        """Set the answer field name to be used in the report mixin."""
        return "answers_ids"
