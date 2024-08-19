# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import uuid

import werkzeug

from odoo import _, api, exceptions, fields, models
from odoo.tools import is_html_empty


class OFSurveySurvey(models.Model):
    """Settings for a multi-page/multi-question survey. Each survey can have one or more attached pages
    and each page can display one or more questions."""

    _name = 'of.survey.survey'
    _description = "Survey"
    _order = 'create_date DESC'
    _rec_name = 'title'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    survey_type = fields.Selection(
        required=True, default='lead_opportunity', selection=[('lead_opportunity', "Lead/Opportunity")]
    )

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        # allows to propagate the text one write in a many2one widget after
        # clicking on 'Create and Edit...' to the popup form.
        if 'title' in fields_list and not result.get('title') and self.env.context.get('default_name'):
            result['title'] = self.env.context.get('default_name')
        return result

    # description
    title = fields.Char(string="Survey Title", required=True, translate=True)
    color = fields.Integer(string="Color Index", default=0)
    description = fields.Html(
        translate=True,
        sanitize=True,
        sanitize_overridable=True,
        help="The description will be displayed on the home page of the survey. You can use this to give the purpose "
        "and guidelines to your candidates before they start it.",
    )
    description_done = fields.Html(
        "End Message", translate=True, help="This message will be displayed when survey is completed"
    )

    background_image = fields.Image()
    background_image_url = fields.Char(string="Background Url", compute='_compute_background_image_url')
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Responsible",
        domain=[('share', '=', False)],
        tracking=True,
        default=lambda self: self.env.user,
    )
    # questions
    question_and_page_ids = fields.One2many(
        comodel_name='of.survey.question', inverse_name='survey_id', string="Sections and Questions", copy=True
    )
    page_ids = fields.One2many(
        comodel_name='of.survey.question', string="Pages", compute='_compute_page_and_question_ids'
    )
    question_ids = fields.One2many(
        comodel_name='of.survey.question', string="Questions", compute='_compute_page_and_question_ids'
    )
    question_count = fields.Integer(string="# Questions", compute='_compute_page_and_question_ids')
    questions_layout = fields.Selection(
        selection=[
            ('page_per_question', "One page per question"),
            ('page_per_section', "One page per section"),
            ('one_page', "One page with all the questions"),
        ],
        string="Pagination",
        required=True,
        default='one_page',
    )
    questions_selection = fields.Selection(
        selection=[('all', "All questions")],
        string="Question Selection",
        required=True,
        default='all',
        help="If randomized is selected, you can configure the number of random questions by section. This mode is "
        "ignored in live session.",
    )
    progression_mode = fields.Selection(
        selection=[('percent', "Percentage left"), ('number', "Number")],
        string="Display Progress as",
        default='percent',
        help="If Number is selected, it will display the number of questions answered on the total number of question "
        "to answer.",
    )
    # attendees
    user_input_ids = fields.One2many(
        comodel_name='of.survey.user_input',
        inverse_name='survey_id',
        string="User responses",
        readonly=True,
        groups='of_survey.group_of_survey_user',
    )
    # security / access
    access_mode = fields.Selection(
        selection=[('public', "Anyone with the link"), ('token', "Invited people only")],
        default='public',
        required=True,
    )
    access_token = fields.Char(default=lambda self: self._get_default_access_token(), copy=False)
    users_login_required = fields.Boolean(
        string="Require Login", help="If checked, users have to login before answering even with a valid token."
    )
    users_can_go_back = fields.Boolean(
        string="Users can go back", help="If checked, users can go back to previous pages.", default=True
    )
    users_can_signup = fields.Boolean(string="Users can signup", compute='_compute_users_can_signup')

    # live sessions - current question fields
    session_question_id = fields.Many2one(
        comodel_name='of.survey.question',
        string="Current Question",
        copy=False,
        help="The current question of the survey session.",
    )
    session_start_time = fields.Datetime(string="Current Session Start Time", copy=False)
    session_question_start_time = fields.Datetime(
        string="Current Question Start Time",
        copy=False,
        help="The time at which the current question has started, used to handle the timer for attendees.",
    )
    session_answer_count = fields.Integer(string="Answers Count", compute='_compute_session_answer_count')
    session_question_answer_count = fields.Integer(
        string="Question Answers Count", compute='_compute_session_question_answer_count'
    )

    # conditional questions management
    has_conditional_questions = fields.Boolean(
        string="Contains conditional questions", compute='_compute_has_conditional_questions'
    )

    # page display
    show_start = fields.Boolean(string="Show start page")
    show_end = fields.Boolean(string="Show end page")

    _sql_constraints = [
        ('access_token_unique', 'unique(access_token)', "Access token should be unique"),
    ]

    @api.depends('background_image', 'access_token')
    def _compute_background_image_url(self):
        self.background_image_url = False
        for survey in self.filtered(lambda survey: survey.background_image and survey.access_token):
            survey.background_image_url = f'/of_survey/{survey.access_token}/get_background_image'

    def _compute_users_can_signup(self):
        signup_allowed = self.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'
        for survey in self:
            survey.users_can_signup = signup_allowed

    @api.depends('question_and_page_ids')
    def _compute_page_and_question_ids(self):
        for survey in self:
            survey.page_ids = survey.question_and_page_ids.filtered(lambda question: question.is_page)
            survey.question_ids = survey.question_and_page_ids - survey.page_ids
            survey.question_count = len(survey.question_ids)

    @api.depends('session_start_time', 'user_input_ids')
    def _compute_session_answer_count(self):
        """We have to loop since our result is dependent of the survey.session_start_time.
        This field is currently used to display the count about a single survey, in the
        context of sessions, so it should not matter too much."""

        for survey in self:
            answer_count = 0
            if input_count := self.env['of.survey.user_input']._read_group(
                [
                    ('survey_id', '=', survey.id),
                    ('is_session_answer', '=', True),
                    ('state', '!=', 'done'),
                    ('create_date', '>=', survey.session_start_time),
                ],
                ['create_uid:count'],
                ['survey_id'],
            ):
                answer_count = input_count[0].get('create_uid', 0)

            survey.session_answer_count = answer_count

    @api.depends('session_question_id', 'session_start_time', 'user_input_ids.user_input_line_ids')
    def _compute_session_question_answer_count(self):
        """We have to loop since our result is dependent of the survey.session_question_id and
        the survey.session_start_time.
        This field is currently used to display the count about a single survey, in the
        context of sessions, so it should not matter too much."""
        for survey in self:
            answer_count = 0
            if input_line_count := self.env['of.survey.user_input.line']._read_group(
                [
                    ('question_id', '=', survey.session_question_id.id),
                    ('survey_id', '=', survey.id),
                    ('create_date', '>=', survey.session_start_time),
                ],
                ['user_input_id:count_distinct'],
                ['question_id'],
            ):
                answer_count = input_line_count[0].get('user_input_id', 0)

            survey.session_question_answer_count = answer_count

    @api.depends('question_and_page_ids.is_conditional')
    def _compute_has_conditional_questions(self):
        for survey in self:
            survey.has_conditional_questions = any(question.is_conditional for question in survey.question_and_page_ids)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def copy_data(self, default=None):
        new_defaults = {'title': _("%s (copy)") % (self.title)}
        default = dict(new_defaults, **(default or {}))
        return super().copy_data(default)

    def write(self, vals):
        res = super().write(vals)
        self._check_conditional_questions()  # FIXME see docstring of this method
        return res

    # ------------------------------------------------------------
    # ANSWER MANAGEMENT
    # ------------------------------------------------------------

    def _create_answer(
        self, user=False, partner=False, email=False, test_entry=False, check_attempts=True, **additional_vals
    ):
        """Main entry point to get a token back or create a new one. This method
        does check for current user access in order to explicitely validate
        security.

        :param user: target user asking for a token; it might be void or a
            public user in which case an email is welcomed;
        :param email: email of the person asking the token is no user exists;
        """
        self.check_access_rights('read')
        self.check_access_rule('read')

        user_inputs = self.env['of.survey.user_input']
        for survey in self:
            if partner and not user and partner.user_ids:
                user = partner.user_ids[0]

            invite_token = additional_vals.pop('invite_token', False)
            survey._check_answer_creation(
                user, partner, email, test_entry=test_entry, check_attempts=check_attempts, invite_token=invite_token
            )
            answer_vals = {
                'survey_id': survey.id,
                'test_entry': test_entry,
            }
            if user and not user._is_public():
                answer_vals['partner_id'] = user.partner_id.id
                answer_vals['email'] = user.email
                answer_vals['nickname'] = user.name
            elif partner:
                answer_vals['partner_id'] = partner.id
                answer_vals['email'] = partner.email
                answer_vals['nickname'] = partner.name
            else:
                answer_vals['email'] = email
                answer_vals['nickname'] = email

            if invite_token:
                answer_vals['invite_token'] = invite_token

            answer_vals |= additional_vals
            user_inputs += user_inputs.create(answer_vals)

        for question in self.mapped('question_ids').filtered(
            lambda q: q.question_type == 'char_box' and (q.save_as_email)
        ):
            for user_input in user_inputs:
                if question.save_as_email and user_input.email:
                    user_input.save_lines(question, user_input.email)

        return user_inputs

    def _check_answer_creation(self, user, partner, email, test_entry=False, check_attempts=True, invite_token=False):
        """Ensure conditions to create new tokens are met."""
        self.ensure_one()
        if test_entry:
            # the current user must have the access rights to survey
            if not user.has_group('of_survey.group_of_survey_user'):
                raise exceptions.UserError(_('Creating test token is not allowed for you.'))
        else:
            if not self.active:
                raise exceptions.UserError(_('Creating token for closed/archived surveys is not allowed.'))
            if self.access_mode == 'authentication':
                # signup possible -> should have at least a partner to create an account
                if self.users_can_signup and not user and not partner:
                    raise exceptions.UserError(
                        _('Creating token for external people is not allowed for surveys requesting authentication.')
                    )
                # no signup possible -> should be a not public user (employee or portal users)
                if not self.users_can_signup and (not user or user._is_public()):
                    raise exceptions.UserError(
                        _('Creating token for external people is not allowed for surveys requesting authentication.')
                    )
            if self.access_mode == 'internal' and (not user or not user._is_internal()):
                raise exceptions.UserError(
                    _('Creating token for anybody else than employees is not allowed for internal surveys.')
                )

    def _prepare_user_input_predefined_questions(self):
        """Will generate the questions for a randomized survey.
        It uses the random_questions_count of every sections of the survey to
        pick a random number of questions and returns the merged recordset"""
        self.ensure_one()

        questions = self.env['of.survey.question']

        # First append questions without page
        for question in self.question_ids:
            if not question.page_id:
                questions |= question

        # Then, questions in sections

        for page in self.page_ids:
            questions |= page.question_ids
        return questions

    def _can_go_back(self, answer, page_or_question):
        """Check if the user can go back to the previous question/page for the currently
        viewed question/page.
        Back button needs to be configured on survey and, depending on the layout:
        - In 'page_per_section', we can go back if we're not on the first page
        - In 'page_per_question', we can go back if:
            - It is not a session answer (doesn't make sense to go back in session context)
            - We are not on the first question
            - The survey does not have pages OR this is not the first page of the survey
                (pages are displayed in 'page_per_question' layout when they have a description, see PR#44271)
        """
        self.ensure_one()
        if self.users_can_go_back and answer.state == 'in_progress':
            if self.questions_layout == 'page_per_section' and page_or_question != self.page_ids[0]:
                return True
            elif (
                self.questions_layout == 'page_per_question'
                and not answer.is_session_answer
                and page_or_question != answer.predefined_question_ids[0]
                and (not self.page_ids or page_or_question != self.page_ids[0])
            ):
                return True

        return False

    # ------------------------------------------------------------
    # QUESTIONS MANAGEMENT
    # ------------------------------------------------------------

    @api.model
    def _get_pages_or_questions(self, user_input):
        """Returns the pages or questions (depending on the layout) that will be shown
        to the user taking the survey.
        In 'page_per_question' layout, we also want to show pages that have a description."""

        result = self.env['of.survey.question']
        if self.questions_layout == 'page_per_section':
            result = self.page_ids
        elif self.questions_layout == 'page_per_question':
            result = self._get_pages_and_questions_to_show()
        return result

    def _get_pages_and_questions_to_show(self):
        """
        :return: survey.question recordset excluding invalid conditional questions and pages without description
        """
        self.ensure_one()
        valid_questions = self.question_and_page_ids.filtered(lambda q: q.is_valid_condition()).sorted()
        return valid_questions + self.question_and_page_ids.filtered(
            lambda q: q.is_page and not is_html_empty(q.description)
        )

    def _get_next_page_or_question(self, user_input, page_or_question_id, go_back=False):
        """Generalized logic to retrieve the next question or page to show on the survey.
        It's based on the page_or_question_id parameter, that is usually the currently displayed question/page.

        There is a special case when the survey is configured with conditional questions:
        - for "page_per_question" layout, the next question to display depends on the selected answers and
            the questions 'hierarchy'.
        - for "page_per_section" layout, before returning the result, we check that it contains at least a question
            (all section questions could be disabled based on previously selected answers)

        The whole logic is inverted if "go_back" is passed as True.

        As pages with description are considered as potential question to display, we show the page
        if it contains at least one active question or a description.

        :param user_input: user's answers
        :param page_or_question_id: current page or question id
        :param go_back: reverse the logic and get the PREVIOUS question/page
        :return: next or previous question/page
        """

        survey = user_input.survey_id
        pages_or_questions = survey._get_pages_or_questions(user_input)
        question_record = self.env['of.survey.question']

        # Get Next
        if not go_back:
            if not pages_or_questions:
                return question_record
            # First page
            if page_or_question_id == 0:
                return pages_or_questions[0]

        current_page_index = pages_or_questions.ids.index(page_or_question_id)

        # Get previous and we are on first page  OR Get Next and we are on last page
        if (go_back and current_page_index == 0) or (not go_back and current_page_index == len(pages_or_questions) - 1):
            return question_record

        # Conditional Questions Management
        inactive_questions = user_input._get_inactive_conditional_questions()
        if survey.questions_layout == 'page_per_question':
            question_candidates = (
                pages_or_questions[:current_page_index] if go_back else pages_or_questions[current_page_index + 1 :]
            )
            for question in question_candidates.sorted(reverse=go_back):
                # pages with description are potential questions to display (are part of question_candidates)
                if question.is_page:
                    contains_active_question = any(
                        sub_question not in inactive_questions for sub_question in question.question_ids
                    )
                    is_description_section = not question.question_ids and not is_html_empty(question.description)
                    if contains_active_question or is_description_section:
                        return question
                else:
                    # ici on doit regarder si la question est affichable ou non selon les conditions
                    if user_input.is_valid_question(question):
                        return question
        elif survey.questions_layout == 'page_per_section':
            section_candidates = (
                pages_or_questions[:current_page_index] if go_back else pages_or_questions[current_page_index + 1 :]
            )
            for section in section_candidates.sorted(reverse=go_back):
                contains_active_question = any(question not in inactive_questions for question in section.question_ids)
                is_description_section = not section.question_ids and not is_html_empty(section.description)
                if contains_active_question or is_description_section:
                    return section
            return question_record

    def _is_first_page_or_question(self, page_or_question):
        """This method checks if the given question or page is the first one to display.
        If the first section of the survey as a description, this will be the first screen to display.
        else, the first question will be the first screen to be displayed.
        This methods is used for survey session management where the host should not be able to go back on the
        first page or question."""
        first_section_has_description = self.page_ids and not is_html_empty(self.page_ids[0].description)
        return (first_section_has_description and page_or_question == self.page_ids[0]) or (
            not first_section_has_description and page_or_question == self.question_ids[0]
        )

    def _is_last_page_or_question(self, user_input, page_or_question):
        """This method checks if the given question or page is the last one.
        This includes conditional questions configuration. If the given question is normally not the last one but
        every following questions are inactive due to conditional questions configurations (and user choices),
        the given question will be the last one, except if the given question is conditioning at least
        one of the following questions.
        For section, we check in each following section if there is an active question.
        If yes, the given page is not the last one.
        """
        pages_or_questions = self._get_pages_or_questions(user_input)
        current_page_index = pages_or_questions.ids.index(page_or_question.id)
        if next_page_or_question_candidates := pages_or_questions[current_page_index + 1 :]:
            inactive_questions = user_input._get_inactive_conditional_questions()
            if self.questions_layout == 'page_per_question':
                next_active_question = any(
                    next_question not in inactive_questions for next_question in next_page_or_question_candidates
                )
                is_triggering_question = user_input.is_valid_question(page_or_question)
                return not (next_active_question or is_triggering_question)
            elif self.questions_layout == 'page_per_section':
                is_triggering_section = any(
                    user_input.is_valid_question(question) for question in page_or_question.question_ids
                )
                next_active_question = False
                for section in next_page_or_question_candidates:
                    next_active_question = any(
                        next_question not in inactive_questions for next_question in section.question_ids
                    )
                    if next_active_question:
                        break
                return not (next_active_question or is_triggering_section)

        return True

    def _get_survey_questions(self, answer=None, page_id=None, question_id=None):
        """Returns a tuple containing: the survey question and the passed question_id / page_id
        based on the question_layout and the fact that it's a session or not.

        Breakdown of use cases:
        - We are currently running a session
            We return the current session question and it's id
        - The layout is page_per_section
            We return the questions for that page and the passed page_id
        - The layout is page_per_question
            We return the question for the passed question_id and the question_id
        - The layout is one_page
            We return all the questions of the survey and None

        In addition, we cross the returned questions with the answer.predefined_question_ids,
        that allows to handle the randomization of questions."""

        questions, page_or_question_id = None, None

        if answer and answer.is_session_answer:
            return self.session_question_id, self.session_question_id.id
        if self.questions_layout == 'page_per_section':
            if not page_id:
                raise ValueError(_("Page id is needed for question layout 'page_per_section'"))
            page_id = int(page_id)
            questions = (
                self.env['of.survey.question'].sudo().search([('survey_id', '=', self.id), ('page_id', '=', page_id)])
            )
            page_or_question_id = page_id
        elif self.questions_layout == 'page_per_question':
            if not question_id:
                raise ValueError(_("Question id is needed for question layout 'page_per_question'"))
            question_id = int(question_id)
            questions = self.env['of.survey.question'].sudo().browse(question_id)
            page_or_question_id = question_id
        else:
            questions = self.question_ids

        # we need the intersection of the questions of this page AND the questions prepared for that user_input
        # (because randomized surveys do not use all the questions of every page)
        if answer:
            questions = questions & answer.predefined_question_ids
        return questions, page_or_question_id

    # ------------------------------------------------------------
    # SESSIONS MANAGEMENT
    # ------------------------------------------------------------

    def _session_open(self):
        """The session start is sudo'ed to allow survey user to manage sessions of surveys
        they do not own.

        We flush after writing to make sure it's updated before bus takes over."""

    def _get_session_most_voted_answers(self):
        """In sessions of survey that has conditional questions, as the survey is passed at the same time by
        many users, we need to extract the most chosen answers, to determine the next questions to display."""

        # get user_inputs from current session
        current_user_inputs = self.user_input_ids.filtered(lambda input: input.create_date > self.session_start_time)
        current_user_input_lines = current_user_inputs.mapped('user_input_line_ids').filtered(
            lambda answer: answer.suggested_answer_id
        )

        # count the number of vote per answer
        votes_by_answer = dict.fromkeys(current_user_input_lines.mapped('suggested_answer_id'), 0)
        for answer in current_user_input_lines:
            votes_by_answer[answer.suggested_answer_id] += 1

        # extract most voted answer for each question
        most_voted_answer_by_questions = dict.fromkeys(current_user_input_lines.mapped('question_id'))
        for question in most_voted_answer_by_questions.keys():
            for answer in votes_by_answer.keys():
                if answer.question_id != question:
                    continue
                most_voted_answer = most_voted_answer_by_questions[question]
                if not most_voted_answer or votes_by_answer[most_voted_answer] < votes_by_answer[answer]:
                    most_voted_answer_by_questions[question] = answer

        # return a fake 'audience' user_input
        fake_user_input = self.env['of.survey.user_input'].new(
            {
                'survey_id': self.id,
                'predefined_question_ids': [(6, 0, self._prepare_user_input_predefined_questions().ids)],
            }
        )

        fake_user_input_lines = self.env['of.survey.user_input.line']
        for question, answer in most_voted_answer_by_questions.items():
            fake_user_input_lines |= self.env['of.survey.user_input.line'].new(
                {
                    'question_id': question.id,
                    'suggested_answer_id': answer.id,
                    'survey_id': self.id,
                    'user_input_id': fake_user_input.id,
                }
            )

        return fake_user_input

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------
    def action_button_open_test_survey(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': _("Test Survey"),
            'target': 'self',
            'url': f'/of_survey/test/{self.access_token}',
        }

    def action_start_survey(self, answer=None):
        """Open the website page with the survey form"""
        self.ensure_one()
        url = '%s?%s' % (
            self.get_start_url(),
            werkzeug.urls.url_encode({'answer_token': answer and answer.access_token or None}),
        )
        return {
            'type': 'ir.actions.act_url',
            'name': "Start Survey",
            'target': 'self',
            'url': url,
        }

    def action_survey_user_input_completed(self):
        action = self.env['ir.actions.act_window']._for_xml_id('of_survey.action_survey_user_input')
        ctx = dict(self.env.context)
        ctx |= {'search_default_survey_id': self.ids[0], 'search_default_completed': 1}
        action['context'] = ctx
        return action

    def get_start_url(self):
        return f'/of_survey/start/{self.access_token}'

    def get_start_short_url(self):
        """See controller method docstring for more details."""
        return f'/of_s/{self.access_token[:6]}'

    def get_print_url(self):
        return f'/of_survey/print/{self.access_token}'

    def _check_conditional_questions(self):
        """
        Checks if there are any conditional questions in the survey and updates the 'is_conditional' field accordingly.

        This method is a hack to avoid an error when opening a survey with conditional questions.
        The error is due to the fact that a question can be deleted and still be part of a condition.
        This method should be improved in the future.

        Returns:
            None
        """
        for survey in self:
            for question in survey.question_ids:
                if len(question.conditional_questions) == 0:
                    question.is_conditional = False
                else:
                    # Check if there are any invalid conditions
                    invalid_conditions = question.conditional_questions.filtered(
                        lambda item: not item.question_id or not item.answer_ids
                    )
                    invalid_conditions.unlink()
                    if not question.conditional_questions:
                        question.is_conditional = False
