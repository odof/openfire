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
    of_survey_user_input = fields.Many2one(comodel_name='of.survey.user_input', string="Survey User Input")
    of_survey_user_input_line = fields.One2many(
        comodel_name='of.survey.user_input.line',
        related='of_survey_user_input.user_input_line_ids',
        string="Surver User Input Line",
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

    @api.depends('of_survey_user_input_line', 'of_question_ids')
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
                        lead.of_survey_user_input_line.filtered(lambda r: r.question_id.id == question.id).mapped(
                            'display_name'
                        )
                    )
                if len(question_answers) == 1:
                    if question_answers.answers != answers:
                        question_answers_ids.append(
                            Command.update(
                                question_answers.id, {'answers': answers, 'user_input': lead.of_survey_user_input.id}
                            )
                        )
                else:
                    question_answers_value = {
                        'question_id': question.id,
                        'answers': answers,
                        'sequence': question.sequence,
                        'user_input': lead.of_survey_user_input.id,
                    }
                    question_answers_ids.append(Command.create(question_answers_value))
            lead.of_answers_ids = question_answers_ids

    @api.onchange('of_survey_id')
    def _onchange_of_survey_id(self):
        if self.of_survey_id:
            self.of_answers_ids = False
            self.of_survey_user_input = self.of_survey_id._create_answer(user=self.env.user, email=self.env.user.email)
            self.of_survey_user_input.res_model = self._name
            self.of_survey_user_input.res_id = self._origin.id
            self.of_survey_user_input.redirect_action_id = self.env.ref('crm.crm_lead_action_pipeline').id

    def action_button_open_survey(self):
        # on nettoie les anciennes données
        self.env['of.survey.user_input'].search(
            [
                ('res_model', '=', self._name),
                ('res_id', '=', self._origin.id),
            ]
        ).unlink()
        self.of_survey_user_input = self.of_survey_id._create_answer(user=self.env.user, email=self.env.user.email)
        self.of_survey_user_input.res_model = self._name
        self.of_survey_user_input.res_id = self._origin.id
        self.of_survey_user_input.redirect_action_id = self.env.ref('crm.crm_lead_action_pipeline').id
        url = f'/of_survey/{self.of_survey_id.access_token}/{self.of_survey_user_input.access_token}'
        return {
            'type': 'ir.actions.act_url',
            'name': _("Start Survey"),
            'target': 'self',
            'url': url,
        }
