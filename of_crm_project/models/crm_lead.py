# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_date_project = fields.Date(string="Project date", tracking=True)

    # Linked Partner fields
    of_interlocutor = fields.Many2one(comodel_name='res.partner', string="Interlocutor")
    of_decision_maker = fields.Many2one(comodel_name='res.partner', string="Decision maker")
    of_architect = fields.Many2one(comodel_name='res.partner', string="Architect")
    of_labor_force = fields.Many2one(comodel_name='res.partner', string="Labor force")
    of_prime_contractor = fields.Many2one(comodel_name='res.partner', string="Prime contractor")
    of_engineering_office = fields.Many2one(comodel_name='res.partner', string="Engineering office")

    of_survey_id = fields.Many2one(comodel_name='of.survey.survey', string="Survey")
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
        inverse_name='lead_id',
        string="Question and Answers",
        compute='_compute_question_answers_ids',
        store=True,
        readonly=False,
    )

    @api.depends('of_survey_user_input_line_ids', 'of_question_ids')
    def _compute_question_answers_ids(self):
        for lead in self:
            question_answers_ids = []

            for question in lead.of_question_ids:
                # on recherche si la réponse est la même, si oui, on ne fait rien, sinon on crée
                question_answers = lead.of_answers_ids.filtered(lambda r: r.question_id.id == question.id)
                if question.is_page:
                    # on est sur une section
                    answers = ""
                else:
                    answers = ", ".join(
                        lead.of_survey_user_input_line_ids.filtered(lambda r: r.question_id.id == question.id).mapped(
                            'display_name'
                        )
                    )
                if len(question_answers) == 1:
                    if question_answers.answers != answers:
                        question_answers_ids.append(
                            Command.update(
                                question_answers.id, {'answers': answers, 'user_input': lead.of_survey_user_input_id.id}
                            )
                        )
                else:
                    question_answers_value = {
                        'question_id': question.id,
                        'answers': answers,
                        'sequence': question.sequence,
                        'user_input': lead.of_survey_user_input_id.id,
                    }
                    question_answers_ids.append(Command.create(question_answers_value))
            lead.of_answers_ids = question_answers_ids

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
            self.of_survey_user_input_id.redirect_action_id = self.env.ref('crm.crm_lead_action_pipeline').id
            self.of_survey_user_input_id.menu_id = self.env.ref('crm.crm_menu_root').id

    @api.depends('of_survey_id')
    def _compute_of_survey_user_input_id(self):
        for lead in self:
            if lead.of_survey_id:
                lead.of_survey_user_input_id = lead.of_survey_id._create_answer(
                    user=self.env.user, email=self.env.user.email
                )
                lead.of_survey_user_input_id.res_model = lead._name
                lead.of_survey_user_input_id.res_id = lead._origin.id
                lead.of_survey_user_input_id.redirect_action_id = self.env.ref('crm.crm_lead_action_pipeline').id
                lead.of_survey_user_input_id.menu_id = self.env.ref('crm.crm_menu_root').id

    def action_button_open_survey(self):
        """
        Open the survey associated with the lead.

        We have to create a new user input to allow the user to answer the survey.
        We need to create a new user input each time we open the survey because we need to keep track of the answers
        given by the user.

        Returns:
            dict: An action dictionary to open the survey URL.
        """
        # on nettoie les anciennes données
        self.env['of.survey.user_input'].search(
            [
                ('res_model', '=', self._name),
                ('res_id', '=', self._origin.id),
            ]
        ).unlink()
        self.of_survey_user_input_id = self.of_survey_id._create_answer(user=self.env.user, email=self.env.user.email)
        self.of_survey_user_input_id.res_model = self._name
        self.of_survey_user_input_id.res_id = self._origin.id
        self.of_survey_user_input_id.redirect_action_id = self.env.ref('crm.crm_lead_action_pipeline').id
        self.of_survey_user_input_id.menu_id = self.env.ref('crm.crm_menu_root').id
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
