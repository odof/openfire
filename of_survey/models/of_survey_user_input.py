# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import uuid

from odoo import Command, _, api, fields, models
from odoo.osv.expression import FALSE_LEAF, TRUE_LEAF, is_false
from odoo.tools.safe_eval import safe_eval


class OFSurveyUserInput(models.Model):
    """Metadata for a set of one user's answers to a particular survey"""

    _name = 'of.survey.user_input'
    _description = "Survey User Input"
    _rec_name = "survey_id"
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # answer description
    survey_id = fields.Many2one(
        comodel_name='of.survey.survey', string="Survey", required=True, readonly=True, ondelete='cascade'
    )
    start_datetime = fields.Datetime(string="Start date and time", readonly=True)
    end_datetime = fields.Datetime(string="End date and time", readonly=True)
    state = fields.Selection(
        selection=[
            ('new', "Not started yet"),
            ('in_progress', "In Progress"),
            ('done', "Completed"),
        ],
        string="Status",
        default='new',
        readonly=True,
    )
    test_entry = fields.Boolean(readonly=True)
    last_displayed_page_id = fields.Many2one(comodel_name='of.survey.question', string="Last displayed question/page")
    # identification / access
    access_token = fields.Char(
        string="Identification token", default=lambda self: str(uuid.uuid4()), readonly=True, required=True, copy=False
    )
    invite_token = fields.Char(
        string="Invite token", readonly=True, copy=False
    )  # no unique constraint, as it identifies a pool of attempts
    partner_id = fields.Many2one(comodel_name='res.partner', string="Contact", readonly=True)
    email = fields.Char(readonly=True)
    nickname = fields.Char(help="Attendee nickname, mainly used to identify them in the survey session leaderboard.")
    # questions / answers
    user_input_line_ids = fields.One2many(
        comodel_name='of.survey.user_input.line', inverse_name='user_input_id', string="Answers", copy=True
    )
    predefined_question_ids = fields.Many2many(
        comodel_name='of.survey.question', string="Predefined Questions", readonly=True
    )
    # live sessions
    is_session_answer = fields.Boolean(
        string="Is in a Session", help="Is that user input part of a survey session or not."
    )
    # linked record and redirect action, menu
    res_model = fields.Char(string="Related Document Model", help="Model of the related document.")
    res_id = fields.Integer(string="Related Document ID", help="ID of the related document.")
    redirect_action_id = fields.Many2one(
        comodel_name='ir.actions.act_window',
        string="Redirect Action",
        help="Action to redirect to the related document.",
    )
    menu_id = fields.Many2one(comodel_name='ir.ui.menu', string="Menu")

    _sql_constraints = [
        ('unique_token', 'UNIQUE (access_token)', "An access token must be unique!"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'predefined_question_ids' not in vals:
                suvey_id = vals.get('survey_id', self.env.context.get('default_survey_id'))
                survey = self.env['of.survey.survey'].browse(suvey_id)
                vals['predefined_question_ids'] = [(6, 0, survey._prepare_user_input_predefined_questions().ids)]
        return super().create(vals_list)

    # ------------------------------------------------------------
    # ACTIONS / BUSINESS
    # ------------------------------------------------------------

    def action_print_answers(self):
        """Open the website page with the survey form"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "View Answers",
            'target': 'self',
            'url': f'/of_survey/print/{self.survey_id.access_token}?answer_token={self.access_token}',
        }

    def action_redirect_to_attempts(self):
        self.ensure_one()

        action = self.env['ir.actions.act_window']._for_xml_id('of_survey.action_survey_user_input')
        context = dict(self.env.context or {})

        context['create'] = False
        context['search_default_survey_id'] = self.survey_id.id
        context['search_default_group_by_survey'] = False
        if self.partner_id:
            context['search_default_partner_id'] = self.partner_id.id
        elif self.email:
            context['search_default_email'] = self.email

        action['context'] = context
        return action

    @api.model
    def _generate_invite_token(self):
        return str(uuid.uuid4())

    def _mark_in_progress(self):
        """marks the state as 'in_progress' and updates the start_datetime accordingly."""
        self.write({'start_datetime': fields.Datetime.now(), 'state': 'in_progress'})
        for user_input in self:
            user_input.predefined_question_ids = user_input.survey_id._prepare_user_input_predefined_questions()

    def get_start_url(self):
        self.ensure_one()
        return f'{self.survey_id.get_start_url()}?answer_token={self.access_token}'

    def get_print_url(self):
        self.ensure_one()
        return f'{self.survey_id.get_print_url()}?answer_token={self.access_token}'

    def _mark_done(self):
        """This method will:
        1. mark the state as 'done'
        2. send the certification email with attached document if
        - The survey is a certification
        - It has a certification_mail_template_id set
        - The user succeeded the test
        Will also run challenge Cron to give the certification badge if any."""
        self.write(
            {
                'end_datetime': fields.Datetime.now(),
                'state': 'done',
            }
        )

        for user_input in self:
            # Update predefined_question_id to remove inactive questions
            user_input.predefined_question_ids -= user_input._get_inactive_conditional_questions()

    # ------------------------------------------------------------
    # CREATE / UPDATE LINES FROM SURVEY FRONTEND INPUT
    # ------------------------------------------------------------

    def save_lines(self, question, answer, comment=None, attachments=None):
        """Save answers to questions, depending on question type

        If an answer already exists for question and user_input_id, it will be
        overwritten (or deleted for 'choice' questions) (in order to maintain data consistency).
        """
        if attachments is None:
            attachments = []

        old_answers = self.env['of.survey.user_input.line'].search(
            [('user_input_id', '=', self.id), ('question_id', '=', question.id)]
        )
        if question.question_type in ['char_box', 'text_box', 'date', 'numerical_box']:
            if answer in ("[]", "") and len(attachments) > 0:
                answer = _("See file(s) for the answer")
            self._save_line_simple_answer(question, old_answers, answer, attachments)
            if question.save_as_email and answer:
                self.write({'email': answer})
        elif question.question_type == 'multi_image':
            self._save_line_file(question, old_answers, answer)
        elif question.question_type in ['simple_choice', 'multiple_choice']:
            self._save_line_choice(question, old_answers, answer, comment, attachments)
        elif question.question_type == 'form':
            self._save_line_pdf(question, old_answers, answer)
        else:
            raise AttributeError(f"{question.question_type}: This type of question has no saving function")

    def _save_line_simple_answer(self, question, old_answers, answer, attachments):
        vals = self._get_line_answer_values(question, answer, question.question_type, attachments)
        if not old_answers:
            return self.env['of.survey.user_input.line'].create(vals)

        old_answers.write(vals)

        return old_answers

    def _save_line_file(self, question, old_answers, answer):
        """Save the user's file upload answer for the given question."""
        vals = self._get_line_answer_file_upload_values(question, 'multi_image', answer)
        if old_answers:
            old_answers.write(vals)
        else:
            old_answers = self.env['of.survey.user_input.line'].create(vals)

        return old_answers

    def _save_line_pdf(self, question, old_answers, answer):
        if answer:
            datas = answer.split(",")
            datas = datas[1] if len(datas) > 1 else datas[0]
            answer = bytes(datas, 'utf-8')

        vals = self._get_line_answer_values(question, answer, question.question_type)
        if not old_answers:
            return self.env['of.survey.user_input.line'].create(vals)
        old_answers.write(vals)
        return old_answers

    def _save_line_choice(self, question, old_answers, answers, comment, attachments):
        if not (isinstance(answers, list)):
            answers = [answers]

        if not answers:
            # add a False answer to force saving a skipped line
            # this will make this question correctly considered as skipped in statistics
            answers = [False]

        vals_list = []

        if question.question_type == 'simple_choice':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [
                    self._get_line_answer_values(question, answer, 'suggestion', attachments) for answer in answers
                ]
        elif question.question_type == 'multiple_choice':
            vals_list = [
                self._get_line_answer_values(question, answer, 'suggestion', attachments) for answer in answers
            ]

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment, attachments))

        old_answers.sudo().unlink()
        return self.env['of.survey.user_input.line'].create(vals_list)

    def _get_line_answer_values(self, question, answer, answer_type, attachments=None):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }

        if not answer or (isinstance(answer, str) and not answer.strip()):
            if len(attachments) == 0:
                vals.update(answer_type=None, skipped=True)
                return vals

        if answer_type == 'suggestion':
            if not answer or (isinstance(answer, str) and not answer.strip()):
                vals['suggested_answer_id'] = False
            else:
                vals['suggested_answer_id'] = int(answer)
        elif answer_type == 'numerical_box':
            vals['value_numerical_box'] = float(answer)
        else:
            if not answer or (isinstance(answer, str) and not answer.strip()):
                if len(attachments) > 0:
                    answer = _("See file(s) for the answer")

            vals[f'value_{answer_type}'] = answer

        # si la question permet d'ajouter des images, il faut aussi les mettre
        if question.add_pictures:
            attachment_ids = []
            image_obj = self.env['of.image']
            for attachment in attachments:
                name = attachment.get('title')
                if name == '':
                    name = attachment.get('filename')
                # on regarde dans la data si on a l'information que c'est une image ou pas
                # si c'est le cas, on prends la deuxième partie du contenu qui est l'image en elle même
                datas = attachment['src'].split(',')
                if len(datas) > 1:
                    datas = datas[1]
                else:
                    datas = datas[0]
                datas = bytes(datas, 'utf-8')

                att = image_obj.search(
                    [
                        ('name', '=', name),
                        ('caption', '=', attachment.get('legend', '')),
                    ],
                    limit=1,
                )

                if not att:
                    att = image_obj.create(
                        {
                            'name': name,
                            'caption': attachment.get('legend', ''),
                            'image_1920': datas,
                        }
                    )
                attachment_ids.append(att.id)
            vals['value_image_ids'] = [Command.set(attachment_ids)]
        return vals

    def _get_line_comment_values(self, question, comment, attachments):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': 'char_box',
            'value_char_box': comment,
        }

        # si la question permet d'ajouter des images, il faut aussi les mettre
        if question.add_pictures:
            attachment_ids = []
            for attachment in attachments:
                name = attachment.get('title')
                if name == '':
                    name = attachment.get('filename')
                # on regarde dans la data si on a l'information que c'est une image ou pas
                # si c'est le cas, on prends la deuxième partie du contenu qui est l'image en elle même
                datas = attachment['src'].split(',')
                if len(datas) > 0:
                    datas = datas[1]
                else:
                    datas = datas[0]
                datas = bytes(datas, 'utf-8')

                attachment = self.env['of.image'].create(
                    {
                        'name': name,
                        'caption': attachment.get('legend', ''),
                        'image_1920': datas,
                    }
                )
                attachment_ids.append(attachment.id)
            vals['value_image_ids'] = [Command.set(attachment_ids)]
        return vals

    def _get_line_answer_file_upload_values(self, question, answer_type, answer):
        """Get the values to use when creating or updating a user input line
        for a file upload answer."""
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        if answer_type == 'multi_image':
            if len(answer) > 0:
                attachment_ids = []

                for file in answer[0]:
                    name = file.get('title')
                    if name == '':
                        name = file.get('filename')

                    # on regarde dans la data si on a l'information que c'est une image ou pas
                    # si c'est le cas, on prends la deuxième partie du contenu qui est l'image en elle même
                    datas = file['src'].split(',')
                    if len(datas) > 0:
                        datas = datas[1]
                    else:
                        datas = datas[0]
                    datas = bytes(datas, 'utf-8')

                    attachment = self.env['of.image'].create(
                        {
                            'name': name,
                            'caption': file.get('legend', ''),
                            'image_1920': datas,
                        }
                    )
                    attachment_ids.append(attachment.id)
                vals['value_image_ids'] = [Command.set(attachment_ids)]
            else:
                vals['skipped'] = True
        return vals

    # ------------------------------------------------------------
    # Conditional Questions Management
    # ------------------------------------------------------------

    def filtered_conditional(self, question):
        """L'idée ici c'est de récupérer le domaine conditionnel généré sur la question
        et tester, deux éléments par deux éléments, et remplacer ces deux éléments par un TRUE_LEAF ou FALSE_LEAF
        en fonction de si une réponse ou non répond à cette condition"""
        res = []
        stack = []
        domain = reversed(safe_eval(question.conditional_domain))
        for leaf in domain:
            if leaf in ['|', '&']:
                if len(res) > 1:
                    res = [leaf] + res
                    if len(self.user_input_line_ids.filtered_domain(res)) > 0:
                        stack.append(TRUE_LEAF)
                    else:
                        stack.append(FALSE_LEAF)
                    res = []
                else:
                    stack.append(leaf)
            else:
                res.append(leaf)
        stack = list(reversed(stack))
        return not is_false("", stack)

    def is_valid_question(self, question):
        """Retourne vrai si la question a toutes les conditions réunies"""
        if not question.is_valid_condition():
            return False
        if not question.is_conditional:
            return True
        return self.filtered_conditional(question)

    def _get_selected_suggested_answers(self):
        return self.mapped('user_input_line_ids.suggested_answer_id')

    def _clear_inactive_conditional_answers(self):
        """
        Clean eventual answers on conditional questions that should not have been displayed to user.
        This method is used mainly for page per question survey, a similar method does the same treatment
        at client side for the other survey layouts.
        E.g.: if depending answer was uncheck after answering conditional question, we need to clear answers
                of that conditional question, for two reasons:
                - ensure correct scoring
                - if the selected answer triggers another question later in the survey, if the answer is not cleared,
                a question that should not be displayed to the user will be.

        TODO DBE: Maybe this can be the only cleaning method, even for section_per_page or one_page where
        conditional questions are, for now, cleared in JS directly. But this can be annoying if user typed a long
        answer, changed their mind unchecking depending answer and changed again their mind by rechecking the depending
        answer -> For now, the long answer will be lost. If we use this as the master cleaning method,
        long answer will be cleared only during submit.
        """
        inactive_questions = self._get_inactive_conditional_questions()

        # delete user.input.line on question that should not be answered.
        answers_to_delete = self.user_input_line_ids.filtered(lambda answer: answer.question_id in inactive_questions)
        answers_to_delete.unlink()

    def _get_inactive_conditional_questions(self):
        """Return the questions that should not be answered"""
        inactive_questions = self.env['of.survey.question']
        for question in self.survey_id.question_ids:
            if not self.is_valid_question(question):
                inactive_questions |= question
        return inactive_questions

    def _get_print_questions(self):
        """Get the questions to display : the ones that should have been answered = active questions
            In case of session, active questions are based on most voted answers
        :return: active survey.question browse records
        """
        survey = self.survey_id
        if self.is_session_answer:
            most_voted_answers = survey._get_session_most_voted_answers()
            inactive_questions = most_voted_answers._get_inactive_conditional_questions()
        else:
            inactive_questions = self._get_inactive_conditional_questions()
        return survey.question_ids - inactive_questions

    # ------------------------------------------------------------
    # MESSAGING
    # ------------------------------------------------------------

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        for user_input in self:
            if user_input.partner_id:
                user_input._message_add_suggested_recipient(
                    recipients, partner=user_input.partner_id, reason=_('Survey Participant')
                )
        return recipients
