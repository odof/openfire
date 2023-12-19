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
    )
    of_survey_user_input = fields.Many2one(comodel_name='of.survey.user_input', string="Survey User Input")
    of_survey_user_input_line = fields.One2many(
        comodel_name='of.survey.user_input.line',
        related='of_survey_user_input.user_input_line_ids',
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

    @api.depends('of_template_id')
    def _compute_of_survey_id(self):
        for event in self.filtered(lambda i: i.of_template_id and not i.of_survey_id):
            event.of_survey_id = event.of_template_id.survey_id

    @api.depends('of_survey_user_input_line', 'of_question_ids')
    def _compute_question_answers_ids(self):
        for event in self:
            question_answers_ids = []

            for question in event.of_question_ids:
                # we find out if the answer is the same, if so, we do nothing, if not, we create it.
                question_answers = event.of_answers_ids.filtered(lambda r: r.question_id.id == question.id)
                if question.is_page:
                    # we are on a section
                    answers = ""
                else:
                    answers = ", ".join(
                        event.of_survey_user_input_line.filtered(lambda r: r.question_id.id == question.id).mapped(
                            'display_name'
                        )
                    )
                if len(question_answers) == 1:
                    if question_answers.answers != answers:
                        question_answers_ids.append(Command.update(question_answers.id, {'answers': answers}))
                else:
                    question_answers_value = {
                        'question_id': question.id,
                        'answers': answers,
                        'sequence': question.sequence,
                    }
                    question_answers_ids.append(Command.create(question_answers_value))
            event.of_answers_ids = question_answers_ids

    @api.onchange('of_survey_id')
    def _onchange_of_survey_id(self):
        if self.of_survey_id:
            self.of_answers_ids = False
            self.of_survey_user_input = self.of_survey_id._create_answer(user=self.env.user, email=self.env.user.email)
            self.of_survey_user_input.res_model = self._name
            self.of_survey_user_input.res_id = self._origin.id
            self.of_survey_user_input.redirect_action_id = self.env.ref('calendar.action_calendar_event').id

    def action_button_open_survey(self):
        self.ensure_one()
        # cleaning up old data
        self.env['of.survey.user_input'].search(
            [
                ('res_model', '=', self._name),
                ('res_id', '=', self._origin.id),
            ]
        ).unlink()
        self.of_survey_user_input = self.of_survey_id._create_answer(user=self.env.user, email=self.env.user.email)
        self.of_survey_user_input.res_model = self._name
        self.of_survey_user_input.res_id = self._origin.id
        self.of_survey_user_input.redirect_action_id = self.env.ref('calendar.action_calendar_event').id
        url = f'/of_survey/{self.of_survey_id.access_token}/{self.of_survey_user_input.access_token}'
        return {
            'type': 'ir.actions.act_url',
            'name': _("Start Survey"),
            'target': 'self',
            'url': url,
        }
