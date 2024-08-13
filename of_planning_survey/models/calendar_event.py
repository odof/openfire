# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    of_survey_id = fields.Many2one(
        comodel_name='of.survey.survey',
        string="Survey",
        domain=[('survey_type', '=', 'intervention_survey')],
        compute='_compute_of_survey_id',
        store=True,
        readonly=False,
        help="Select the survey to be answered as part of the intervention",
    )
    of_survey_user_input_id = fields.Many2one(
        comodel_name='of.survey.user_input',
        string="Survey User Input",
        compute='_compute_of_survey_user_input_id',
        store=True,
        readonly=False,
    )
    of_survey_user_input_line_ids = fields.One2many(
        comodel_name='of.survey.user_input.line',
        related='of_survey_user_input_id.user_input_line_ids',
        string="Survey User Input Line",
    )
    of_question_ids = fields.One2many(
        comodel_name='of.survey.question', related='of_survey_id.question_and_page_ids', string="Questions"
    )
    of_answers_ids = fields.One2many(
        comodel_name='of.survey.answers',
        inverse_name='intervention_id',
        string="Question and Answers",
        compute='_compute_question_answers_ids',
        store=True,
        readonly=False,
    )

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends('of_template_id')
    def _compute_of_survey_id(self):
        for event in self:
            event.of_survey_id = event.of_template_id.survey_id

    @api.depends('of_survey_id')
    def _compute_of_survey_user_input_id(self):
        for event in self:
            if event.of_survey_id:
                event.of_survey_user_input_id = event.of_survey_id._create_answer(
                    user=self.env.user, email=self.env.user.email
                )
                event.of_survey_user_input_id.res_model = event._name
                event.of_survey_user_input_id.res_id = event._origin.id
                event.of_survey_user_input_id.redirect_action_id = self.env.ref('calendar.action_calendar_event').id
                event.of_survey_user_input_id.menu_id = self.env.ref('of_planning.menu_of_planning_main').id

    @api.depends('of_survey_user_input_line_ids', 'of_question_ids')
    def _compute_question_answers_ids(self):
        for event in self:
            event.of_answers_ids = False
            question_answers_ids = []

            for question in event.of_question_ids:
                # we find out if the answer is the same, if so, we do nothing, if not, we create it.
                question_answers = event.of_answers_ids.filtered(lambda r: r.question_id.id == question.id)
                if question.is_page:
                    # we are on a section
                    answers = ""
                else:
                    input_lines = event.of_survey_user_input_line_ids.filtered(
                        lambda r: r.question_id.id == question.id
                    )
                    # When we have a multiple choice question with "comment allowed" option, we want to skip the
                    # skipped answers if there is at least one answer given by the user to avoid having something like
                    # `"Ignored, Answered text"` in the answers field.
                    answer_lines = [
                        line.display_name
                        for line in input_lines
                        if len(input_lines.filtered(lambda r: r.question_id.id == line.question_id.id)) <= 1
                        or not line.skipped
                        or line.question_id.question_type != 'multiple_choice'
                    ]
                    answers = ', '.join(answer_lines)

                if len(question_answers) == 1:
                    if question_answers.answers != answers:
                        question_answers_ids.append(
                            Command.update(
                                question_answers.id,
                                {'answers': answers, 'user_input': event.of_survey_user_input_id.id},
                            )
                        )
                else:
                    question_answers_value = {
                        'question_id': question.id,
                        'answers': answers,
                        'sequence': question.sequence,
                        'user_input': event.of_survey_user_input_id.id,
                    }
                    question_answers_ids.append(Command.create(question_answers_value))
            event.of_answers_ids = question_answers_ids

    # --------------------------------------------------------------------------
    # Onchange methods
    # --------------------------------------------------------------------------

    @api.onchange('of_survey_id')
    def _onchange_of_survey_id(self):
        """When the survey is changed we remove the answers and create a new user input.

        We need to do that stuff in the onchange too because the survey can be changed in the view and never opened from
        the button `action_button_open_survey`.

        That case should happen when survey is called from GraphQL API. # TODO: move me in a graphql module ?
        """
        if self.of_survey_id:
            self.of_answers_ids = False
            self.of_survey_user_input_id = self.of_survey_id._create_answer(
                user=self.env.user, email=self.env.user.email
            )
            self.of_survey_user_input_id.res_model = self._name
            self.of_survey_user_input_id.res_id = self._origin.id
            self.of_survey_user_input_id.redirect_action_id = self.env.ref('of_planning.action_calendar_event').id
            self.of_survey_user_input_id.menu_id = self.env.ref('of_planning.menu_of_planning_main').id

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)") % self.name)
        new_record = super().copy(default)
        # by doing this we keep we are resetting questions and user input to avoid having the same answers
        # on the new record
        new_record.of_survey_id = self.of_survey_id
        return new_record

    # --------------------------------------------------------------------------
    # Actions methods
    # --------------------------------------------------------------------------

    def action_button_open_survey(self):
        """
        Open the survey associated with the calendar event.

        We have to create a new user input to allow the user to answer the survey.
        We need to create a new user input each time we open the survey because we need to keep track of the answers
        given by the user.

        Returns:
            dict: An action dictionary to open the survey URL.
        """
        self.ensure_one()
        # cleaning up old data
        self.env['of.survey.user_input'].search(
            [
                ('res_model', '=', self._name),
                ('res_id', '=', self._origin.id),
            ]
        ).unlink()
        self.of_survey_user_input_id = self.of_survey_id._create_answer(user=self.env.user, email=self.env.user.email)
        self.of_survey_user_input_id.res_model = self._name
        self.of_survey_user_input_id.res_id = self._origin.id
        self.of_survey_user_input_id.redirect_action_id = self.env.ref('of_planning.action_calendar_event').id
        self.of_survey_user_input_id.menu_id = self.env.ref('of_planning.menu_of_planning_main').id

        url = f'/of_survey/{self.of_survey_id.access_token}/{self.of_survey_user_input_id.access_token}'
        return {
            'type': 'ir.actions.act_url',
            'name': _("Start Survey"),
            'target': 'self',
            'url': url,
        }

    def action_button_edit_survey(self):
        # on passe le survey en cours
        self.of_survey_user_input_id._mark_in_progress()

        # on met sur la première question
        self.of_survey_user_input_id.last_displayed_page_id = 0

        url = f'/of_survey/{self.of_survey_id.access_token}/{self.of_survey_user_input_id.access_token}'
        return {
            'type': 'ir.actions.act_url',
            'name': _("Edit Survey"),
            'target': 'self',
            'url': url,
        }
