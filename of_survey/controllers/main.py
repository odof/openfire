# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

import werkzeug
from dateutil.relativedelta import relativedelta

from odoo import Command, _, fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.osv import expression
from odoo.tools import format_date, format_datetime, is_html_empty

from odoo.addons.base.models.ir_qweb import keep_query

_logger = logging.getLogger(__name__)


class OFSurvey(http.Controller):
    # ------------------------------------------------------------
    # ACCESS
    # ------------------------------------------------------------

    def _fetch_from_access_token(self, survey_token, answer_token):
        """Check that given token matches an answer from the given survey_id.
        Returns a sudo-ed browse record of survey in order to avoid access rights
        issues now that access is granted through token."""
        survey_sudo = (
            request.env["of.survey.survey"]
            .with_context(active_test=False)
            .sudo()
            .search([("access_token", "=", survey_token)])
        )
        if not answer_token:
            answer_sudo = request.env["of.survey.user_input"].sudo()
        else:
            answer_sudo = (
                request.env["of.survey.user_input"]
                .sudo()
                .search([("survey_id", "=", survey_sudo.id), ("access_token", "=", answer_token)], limit=1)
            )
        return survey_sudo, answer_sudo

    def _check_validity(self, survey_token, answer_token, ensure_token=True, check_partner=False):
        """Check survey is open and can be taken. This does not checks for
        security rules, only functional / business rules. It returns a string key
        allowing further manipulation of validity issues

         * survey_wrong: survey does not exist;
         * survey_auth: authentication is required;
         * survey_closed: survey is closed and does not accept input anymore;
         * survey_void: survey is void and should not be taken;
         * token_wrong: given token not recognized;
         * token_required: no token given although it is necessary to access the
            survey;


        :param ensure_token: whether user input existence based on given access token
            should be enforced or not, depending on the route requesting a token or
            allowing external world calls;

        :param check_partner: Whether we must check that the partner associated to the target
            answer corresponds to the active user.
        """
        survey_sudo, answer_sudo = self._fetch_from_access_token(survey_token, answer_token)

        if not survey_sudo.exists():
            return "survey_wrong"

        if answer_token and not answer_sudo:
            return "token_wrong"

        if not answer_sudo and ensure_token:
            return "token_required"
        if not answer_sudo and survey_sudo.access_mode == "token":
            return "token_required"

        if survey_sudo.users_login_required and request.env.user._is_public():
            return "survey_auth"

        if not survey_sudo.active and (not answer_sudo or not answer_sudo.test_entry):
            return "survey_closed"

        if (
            not survey_sudo.page_ids and survey_sudo.questions_layout == "page_per_section"
        ) or not survey_sudo.question_ids:
            return "survey_void"

        if answer_sudo and check_partner:
            if request.env.user._is_public() and answer_sudo.partner_id and not answer_token:
                # answers from public user should not have any partner_id; this indicates probably a cookie issue
                return "answer_wrong_user"
            if not request.env.user._is_public() and answer_sudo.partner_id != request.env.user.partner_id:
                # partner mismatch, probably a cookie issue
                return "answer_wrong_user"

        return True

    def _get_access_data(self, survey_token, answer_token, ensure_token=True, check_partner=False):
        """Get back data related to survey and user input, given the ID and access
        token provided by the route.

        : param ensure_token: whether user input existence should be enforced or not(see ``_check_validity``)
        : param check_partner: whether the partner of the target answer should be checked (see ``_check_validity``)
        """
        survey_sudo, answer_sudo = request.env["of.survey.survey"].sudo(), request.env["of.survey.user_input"].sudo()
        has_survey_access, can_answer = False, False

        validity_code = self._check_validity(
            survey_token, answer_token, ensure_token=ensure_token, check_partner=check_partner
        )
        if validity_code != "survey_wrong":
            survey_sudo, answer_sudo = self._fetch_from_access_token(survey_token, answer_token)
            try:
                survey_user = survey_sudo.with_user(request.env.user)
                survey_user.check_access_rights("read", raise_exception=True)
                survey_user.check_access_rule("read")
            except Exception:
                _logger.exception("Access error on survey %s for user %s", survey_sudo, request.env.user)
            else:
                has_survey_access = True
            can_answer = bool(answer_sudo) or survey_sudo.access_mode == "public"
        return {
            "survey_sudo": survey_sudo,
            "answer_sudo": answer_sudo,
            "has_survey_access": has_survey_access,
            "can_answer": can_answer,
            "validity_code": validity_code,
        }

    def _redirect_with_error(self, access_data, error_key):
        survey_sudo = access_data["survey_sudo"]
        answer_sudo = access_data["answer_sudo"]

        if error_key == "survey_void" and access_data["can_answer"]:
            return request.render("of_survey.of_survey_void_content", {"survey": survey_sudo, "answer": answer_sudo})
        elif error_key == "survey_closed" and access_data["can_answer"]:
            return request.render("of_survey.of_survey_closed_expired", {"survey": survey_sudo})
        elif error_key == "survey_auth":
            if not answer_sudo:  # survey is not even started
                redirect_url = f"/web/login?redirect=/of_survey/start/{survey_sudo.access_token}"
            elif answer_sudo.access_token:  # survey is started but user is not logged in anymore.
                if answer_sudo.partner_id and (answer_sudo.partner_id.user_ids or survey_sudo.users_can_signup):
                    if answer_sudo.partner_id.user_ids:
                        answer_sudo.partner_id.signup_cancel()
                    else:
                        answer_sudo.partner_id.signup_prepare(expiration=fields.Datetime.now() + relativedelta(days=1))
                    redirect_url = answer_sudo.partner_id._get_signup_url_for_action(
                        url=f"/of_survey/start/{survey_sudo.access_token}?answer_token={answer_sudo.access_token}"
                    )[answer_sudo.partner_id.id]
                else:
                    redirect_url = (
                        f"/web/login?redirect=/of_survey/start/{survey_sudo.access_token}?"
                        f"answer_token={answer_sudo.access_token}"
                    )
            return request.render(
                "of_survey.of_survey_auth_required", {"survey": survey_sudo, "redirect_url": redirect_url}
            )

        return request.redirect("/")

    # ------------------------------------------------------------
    # TEST / RETRY SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route("/of_survey/test/<string:survey_token>", type="http", auth="user", website=True)
    def survey_test(self, survey_token, **kwargs):
        """Test mode for surveys: create a test answer, only for managers or officers
        testing their surveys"""
        survey_sudo, dummy = self._fetch_from_access_token(survey_token, False)
        try:
            answer_sudo = survey_sudo._create_answer(user=request.env.user, test_entry=True)
            answer_sudo.res_model = survey_sudo._name
            answer_sudo.res_id = survey_sudo.id
            answer_sudo.redirect_action_id = request.env.ref("of_survey.of_action_survey_form").id
            answer_sudo.menu_id = request.env.ref("of_survey.menu_of_survey_form").id
        except Exception as e:
            _logger.info("Error while creating test answer for survey %s: %s", survey_sudo, e)
            return request.redirect("/")
        return request.redirect(
            "/of_survey/start/%s?%s"
            % (survey_sudo.access_token, keep_query("*", answer_token=answer_sudo.access_token))
        )

    @http.route(
        "/of_survey/retry/<string:survey_token>/<string:answer_token>", type="http", auth="public", website=True
    )
    def survey_retry(self, survey_token, answer_token, **post):
        """This route is called whenever the user has attempts left and hits the 'Retry' button
        after failing the survey."""
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data["validity_code"] is not True:
            return self._redirect_with_error(access_data, access_data["validity_code"])

        survey_sudo, answer_sudo = access_data["survey_sudo"], access_data["answer_sudo"]
        if not answer_sudo:
            # attempts to 'retry' without having tried first
            return request.redirect("/")

        try:
            retry_answer_sudo = survey_sudo._create_answer(
                user=request.env.user,
                partner=answer_sudo.partner_id,
                email=answer_sudo.email,
                invite_token=answer_sudo.invite_token,
                test_entry=answer_sudo.test_entry,
                **{},
            )
        except Exception:
            return request.redirect("/")
        return request.redirect(
            "/of_survey/start/%s?%s"
            % (survey_sudo.access_token, keep_query("*", answer_token=retry_answer_sudo.access_token))
        )

    def _prepare_survey_finished_values(self, survey, answer, token=False):
        values = {"survey": survey, "answer": answer}
        if token:
            values["token"] = token
        return values

    # ------------------------------------------------------------
    # TAKING SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route("/of_survey/start/<string:survey_token>", type="http", auth="public", website=True)
    def survey_start(self, survey_token, answer_token=None, email=False, **post):
        """Start a survey by providing
        * a token linked to a survey;
        * a token linked to an answer or generate a new token if access is allowed;
        """
        # Get the current answer token from cookie
        answer_from_cookie = False
        if not answer_token:
            answer_token = request.httprequest.cookies.get(f"survey_{survey_token}")
            answer_from_cookie = bool(answer_token)

        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if answer_from_cookie and access_data["validity_code"] in ("answer_wrong_user", "token_wrong"):
            # If the cookie had been generated for another user or does not correspond to any existing answer object
            # (probably because it has been deleted), ignore it and redo the check.
            # The cookie will be replaced by a legit value when resolving the URL, so we don't clean it further here.
            access_data = self._get_access_data(survey_token, None, ensure_token=False)

        if access_data["validity_code"] is not True:
            return self._redirect_with_error(access_data, access_data["validity_code"])

        survey_sudo, answer_sudo = access_data["survey_sudo"], access_data["answer_sudo"]
        if not answer_sudo:
            try:
                answer_sudo = survey_sudo._create_answer(user=request.env.user, email=email)
            except UserError:
                answer_sudo = False

        if not answer_sudo:
            try:
                survey_sudo.with_user(request.env.user).check_access_rights("read")
                survey_sudo.with_user(request.env.user).check_access_rule("read")
            except Exception:
                return request.redirect("/")
            else:
                return request.render("of_survey.of_survey_403_page", {"survey": survey_sudo})

        return request.redirect(f"/of_survey/{survey_sudo.access_token}/{answer_sudo.access_token}")

    def _prepare_survey_data(self, survey_sudo, answer_sudo, **post):
        """This method prepares all the data needed for template rendering, in function of the survey user input state.
        :param post:
            - previous_page_id : come from the breadcrumb or the back button and force the next questions to load
                to be the previous ones."""
        data = {
            "is_html_empty": is_html_empty,
            "survey": survey_sudo,
            "answer": answer_sudo,
            "breadcrumb_pages": [
                {
                    "id": page.id,
                    "title": page.title,
                }
                for page in survey_sudo.page_ids
            ],
            "format_datetime": lambda dt: format_datetime(request.env, dt, dt_format=False),
            "format_date": lambda date: format_date(request.env, date),
        }

        if not answer_sudo.is_session_answer and answer_sudo.start_datetime:
            data |= {
                "server_time": fields.Datetime.now(),
                "timer_start": answer_sudo.start_datetime.isoformat(),
            }

        page_or_question_key = "question" if survey_sudo.questions_layout == "page_per_question" else "page"

        # Bypass all if page_id is specified (comes from breadcrumb or previous button)
        if "previous_page_id" in post:
            previous_page_or_question_id = int(post["previous_page_id"])
            new_previous_id = survey_sudo._get_next_page_or_question(
                answer_sudo, previous_page_or_question_id, go_back=True
            ).id
            page_or_question = request.env["of.survey.question"].sudo().browse(previous_page_or_question_id)
            data |= {
                page_or_question_key: page_or_question,
                "previous_page_id": new_previous_id,
                "has_answered": answer_sudo.user_input_line_ids.filtered(
                    lambda line: line.question_id.id == new_previous_id
                ),
                "can_go_back": survey_sudo._can_go_back(answer_sudo, page_or_question),
            }
            return data

        if answer_sudo.state == "in_progress":
            if answer_sudo.is_session_answer:
                next_page_or_question = survey_sudo.session_question_id
            else:
                next_page_or_question = survey_sudo._get_next_page_or_question(
                    answer_sudo, answer_sudo.last_displayed_page_id.id if answer_sudo.last_displayed_page_id else 0
                )

                if next_page_or_question:
                    data["survey_last"] = survey_sudo._is_last_page_or_question(answer_sudo, next_page_or_question)

            if answer_sudo.is_session_answer:
                data |= {
                    "timer_start": survey_sudo.session_question_start_time.isoformat(),
                }

            data |= {
                page_or_question_key: next_page_or_question,
                "has_answered": answer_sudo.user_input_line_ids.filtered(
                    lambda line: line.question_id == next_page_or_question
                ),
                "can_go_back": survey_sudo._can_go_back(answer_sudo, next_page_or_question),
            }
            if survey_sudo.questions_layout != "one_page":
                data["previous_page_id"] = survey_sudo._get_next_page_or_question(
                    answer_sudo, next_page_or_question.id, go_back=True
                ).id
        elif answer_sudo.state == "done":
            # Display success message
            return self._prepare_survey_finished_values(survey_sudo, answer_sudo)
        return data

    def _prepare_question_html(self, survey_sudo, answer_sudo, **post):
        """Survey page navigation is done in AJAX. This function prepare the 'next page' to display in html
        and send back this html to the survey_form widget that will inject it into the page.
        Background url must be given to the caller in order to process its refresh as we don't have the next question
        object at frontend side."""
        survey_data = self._prepare_survey_data(survey_sudo, answer_sudo, **post)

        if answer_sudo.state == "done":
            survey_content = request.env["ir.qweb"]._render("of_survey.survey_fill_form_done", survey_data)
        else:
            survey_content = request.env["ir.qweb"]._render("of_survey.survey_fill_form_in_progress", survey_data)

        survey_progress = False
        if (
            answer_sudo.state == "in_progress"
            and not survey_data.get("question", request.env["of.survey.question"]).is_page
        ):
            if survey_sudo.questions_layout == "page_per_section":
                page_ids = survey_sudo.page_ids.ids
                survey_progress = request.env["ir.qweb"]._render(
                    "of_survey.survey_progression",
                    {
                        "survey": survey_sudo,
                        "page_ids": page_ids,
                        "page_number": page_ids.index(survey_data["page"].id)
                        + (1 if survey_sudo.progression_mode == "number" else 0),
                    },
                )
            elif survey_sudo.questions_layout == "page_per_question":
                page_ids = (
                    survey_sudo.question_ids.ids
                    if answer_sudo.is_session_answer
                    else answer_sudo.predefined_question_ids.ids
                )
                survey_progress = request.env["ir.qweb"]._render(
                    "of_survey.survey_progression",
                    {
                        "survey": survey_sudo,
                        "page_ids": page_ids,
                        "page_number": page_ids.index(survey_data["question"].id),
                    },
                )

        background_image_url = survey_sudo.background_image_url
        if "question" in survey_data:
            background_image_url = survey_data["question"].background_image_url
        elif "page" in survey_data:
            background_image_url = survey_data["page"].background_image_url

        return {
            "survey_content": survey_content,
            "survey_progress": survey_progress,
            "survey_navigation": request.env["ir.qweb"]._render("of_survey.of_survey_navigation", survey_data),
            "background_image_url": background_image_url,
        }

    @http.route("/of_survey/<string:survey_token>/<string:answer_token>", type="http", auth="public", website=True)
    def survey_display_page(self, survey_token, answer_token, **post):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data["validity_code"] is not True:
            return self._redirect_with_error(access_data, access_data["validity_code"])

        answer_sudo = access_data["answer_sudo"]

        return request.render(
            "of_survey.survey_page_fill", self._prepare_survey_data(access_data["survey_sudo"], answer_sudo, **post)
        )

    # ---------------------------------------------------------------------------
    # ROUTES to handle question images + survey background transitions + Tool
    # ---------------------------------------------------------------------------

    @http.route(
        "/of_survey/<string:survey_token>/get_background_image", type="http", auth="public", website=True, sitemap=False
    )
    def survey_get_background(self, survey_token):
        survey_sudo, dummy = self._fetch_from_access_token(survey_token, False)
        return request.env["ir.binary"]._get_image_stream_from(survey_sudo, "background_image").get_response()

    @http.route(
        "/of_survey/<string:survey_token>/<int:section_id>/get_background_image",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def survey_section_get_background(self, survey_token, section_id):
        survey_sudo, dummy = self._fetch_from_access_token(survey_token, False)

        if section := survey_sudo.page_ids.filtered(lambda q: q.id == section_id):
            return request.env["ir.binary"]._get_image_stream_from(section, "background_image").get_response()
        else:
            # trying to access a question that is not in this survey
            raise werkzeug.exceptions.Forbidden()

    @http.route(
        "/of_survey/get_question_image/<string:survey_token>/<string:answer_token>/<int:question_id>/"
        "<int:suggested_answer_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def survey_get_question_image(self, survey_token, answer_token, question_id, suggested_answer_id):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data["validity_code"] is not True:
            return werkzeug.exceptions.Forbidden()

        survey_sudo = access_data["survey_sudo"]

        suggested_answer = False
        if int(question_id) in survey_sudo.question_ids.ids:
            suggested_answer = (
                request.env["of.survey.question.answer"]
                .sudo()
                .search(
                    [
                        ("id", "=", int(suggested_answer_id)),
                        ("question_id", "=", int(question_id)),
                        ("question_id.survey_id", "=", survey_sudo.id),
                    ]
                )
            )

        if not suggested_answer:
            return werkzeug.exceptions.NotFound()

        return request.env["ir.binary"]._get_image_stream_from(suggested_answer, "value_image").get_response()

    # ----------------------------------------------------------------
    # JSON ROUTES to begin / continue survey (ajax navigation) + Tools
    # ----------------------------------------------------------------

    @http.route(
        "/of_survey/begin/<string:survey_token>/<string:answer_token>", type="json", auth="public", website=True
    )
    def survey_begin(self, survey_token, answer_token, **post):
        """Route used to start the survey user input and display the first survey page."""
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data["validity_code"] is not True:
            return {"error": access_data["validity_code"]}
        survey_sudo, answer_sudo = access_data["survey_sudo"], access_data["answer_sudo"]

        if answer_sudo.state != "new":
            return {"error": _("The survey has already started.")}

        answer_sudo._mark_in_progress()
        return self._prepare_question_html(survey_sudo, answer_sudo, **post)

    @http.route(
        "/of_survey/next_question/<string:survey_token>/<string:answer_token>", type="json", auth="public", website=True
    )
    def survey_next_question(self, survey_token, answer_token, **post):
        """Method used to display the next survey question in an ongoing session.
        Triggered on all attendees screens when the host goes to the next question."""
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data["validity_code"] is not True:
            return {"error": access_data["validity_code"]}
        survey_sudo, answer_sudo = access_data["survey_sudo"], access_data["answer_sudo"]

        if answer_sudo.state == "new" and answer_sudo.is_session_answer:
            answer_sudo._mark_in_progress()

        return self._prepare_question_html(survey_sudo, answer_sudo, **post)

    @http.route(
        "/of_survey/submit/<string:survey_token>/<string:answer_token>", type="json", auth="public", website=True
    )
    def survey_submit(self, survey_token, answer_token, **post):
        """Submit a page from the survey.
        This will take into account the validation errors and store the answers to the questions.
        If the time limit is reached, errors will be skipped, answers will be ignored and
        survey state will be forced to 'done'"""
        # Survey Validation
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data["validity_code"] is not True:
            return {"error": access_data["validity_code"]}
        survey_sudo, answer_sudo = access_data["survey_sudo"], access_data["answer_sudo"]
        if answer_sudo.state == "done":
            return {"error": "unauthorized"}

        questions, page_or_question_id = survey_sudo._get_survey_questions(
            answer=answer_sudo, page_id=post.get("page_id"), question_id=post.get("question_id")
        )

        errors = {}
        # Prepare answers / comment by question, validate and save answers
        for question in questions:
            inactive_questions = (
                request.env["of.survey.question"]
                if answer_sudo.is_session_answer
                else answer_sudo._get_inactive_conditional_questions()
            )
            if question in inactive_questions:  # if question is inactive, skip validation and save
                continue
            answer, comment = self._extract_comment_from_answers(question, post.get(str(question.id)))
            errors |= question.validate_question(answer, comment)
            if not errors.get(question.id):
                attachments = post.get("images").get(str(question.id))
                if not attachments:
                    attachments = []
                answer_sudo.save_lines(question, answer, comment, attachments)

        if errors:
            return {"error": "validation", "fields": errors}

        if not answer_sudo.is_session_answer:
            answer_sudo._clear_inactive_conditional_answers()

        if survey_sudo.questions_layout == "one_page":
            answer_sudo._mark_done()
        elif "previous_page_id" in post:
            # when going back, save the last displayed to reload the survey where the user left it.
            answer_sudo.write({"last_displayed_page_id": post["previous_page_id"]})
            # Go back to specific page using the breadcrumb. Lines are saved and survey continues
            return self._prepare_question_html(survey_sudo, answer_sudo, **post)
        else:
            if not answer_sudo.is_session_answer:
                next_page = survey_sudo._get_next_page_or_question(answer_sudo, page_or_question_id)
                if not next_page:
                    answer_sudo._mark_done()

            answer_sudo.write({"last_displayed_page_id": page_or_question_id})

        return self._prepare_question_html(survey_sudo, answer_sudo)

    def _extract_comment_from_answers(self, question, answers):
        """Answers is a custom structure depending of the question type
        that can contain question answers but also comments that need to be
        extracted before validating and saving answers.
        If multiple answers, they are listed in an array
        where answers are structured differently. See input and output for
        more info on data structures.
        :param question: survey.question
        :param answers:
          * question_type: free_text, text_box, numerical_box, date, datetime
            answers is a string containing the value
          * question_type: simple_choice with no comment
            answers is a string containing the value ('question_id_1')
          * question_type: simple_choice with comment
            ['question_id_1', {'comment': str}]
          * question_type: multiple choice
            ['question_id_1', 'question_id_2'] + [{'comment': str}] if holds a comment

        :return: tuple(
          same structure without comment,
          extracted comment for given question,
        )"""
        comment = None
        answers_no_comment = []
        if answers:
            if not isinstance(answers, list):
                answers = [answers]
            for answer in answers:
                if isinstance(answer, dict) and "comment" in answer:
                    comment = answer["comment"].strip()
                else:
                    answers_no_comment.append(answer)

            if len(answers_no_comment) == 1:
                answers_no_comment = answers_no_comment[0]
        return answers_no_comment, comment

    @http.route(
        "/of_survey/conditional-questions-from-answer/<model('of.survey.user_input'):user_input>",
        type="json",
        auth="public",
        website=True,
    )
    def survey_questions_from_answer(self, user_input, **post):
        """Retourne la liste des id des questions suite à l'ajout des réponses"""
        new_user_input = user_input.copy()

        # on reçoit la liste des questions et réponses répondus en ligne par l'utilisateur
        questions_answers = request.params.get("questions_answers")
        # on va créer une liste de question et réponses pour retourner la liste des questions qui sont à afficher
        for question in questions_answers:
            for answer_id in question["answers"]:
                # si la question est déjà dans les réponses, on la supprime
                lines = new_user_input.user_input_line_ids.filtered(lambda r: r.question_id.id == int(question["id"]))
                lines.unlink()
                if answer_id != "-1":  # si la réponse n'est pas un commentaire
                    new_user_input.user_input_line_ids = [
                        Command.create(
                            {
                                "question_id": int(question["id"]),
                                "answer_type": "suggestion",
                                "suggested_answer_id": int(answer_id),
                            },
                        )
                    ]

        # pour chaque question conditionnelle du formulaire, on regarde si cette nouvelle réponse active une question
        conditional_questions = request.env["of.survey.question"]

        questions = new_user_input.survey_id.question_ids.filtered(lambda record: record.is_conditional)
        for question in questions:
            if new_user_input.is_valid_question(question):
                conditional_questions |= question

        # on n'a plus besoin des réponses
        new_user_input.unlink()
        return conditional_questions.ids if len(conditional_questions) > 0 else []

    @http.route(
        '/of_survey/conditional-inactive-questions/<model("of.survey.user_input"):user_input>',
        type="json",
        auth="public",
        website=True,
    )
    def survey_inactive_questions(self, user_input, **post):
        inactive_questions = user_input.sudo()._get_inactive_conditional_questions()
        return inactive_questions.ids if len(inactive_questions) > 0 else []

    @http.route(
        '/of_survey/images/<model("of.survey.user_input"):user_input>', type="json", auth="public", website=True
    )
    def survey_images(self, user_input, **post):
        """
        Retrieve survey images for each question in the user input.
        """
        images = {}
        for line in user_input.user_input_line_ids:
            if line.question_id not in images:
                images[line.question_id.id] = []

            for image in line.value_image_ids:
                images[line.question_id.id].append(
                    {
                        "title": image.name,
                        "legend": image.caption,
                        "src": f"data:image/png;base64,{image.image_1920.decode('utf-8')}",  # noqa E231, E702
                    }
                )
        return images

    # ------------------------------------------------------------
    # COMPLETED SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route("/of_survey/print/<string:survey_token>", type="http", auth="public", website=True, sitemap=False)
    def survey_print(self, survey_token, review=False, answer_token=None, **post):
        """Display an survey in printable view; if <answer_token> is set, it will
        grab the answers of the user_input_id that has <answer_token>."""
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if access_data["validity_code"] is not True and (
            access_data["has_survey_access"]
            or access_data["validity_code"] not in ["token_required", "survey_closed", "survey_void"]
        ):
            return self._redirect_with_error(access_data, access_data["validity_code"])

        survey_sudo, answer_sudo = access_data["survey_sudo"], access_data["answer_sudo"]
        return request.render(
            "of_survey.of_survey_page_print",
            {
                "is_html_empty": is_html_empty,
                "review": review,
                "survey": survey_sudo,
                "answer": answer_sudo,
                "questions_to_display": answer_sudo._get_print_questions(),
                "format_datetime": lambda dt: format_datetime(request.env, dt, dt_format=False),
                "format_date": lambda date: format_date(request.env, date),
            },
        )

    # ------------------------------------------------------------
    # REPORTING SURVEY ROUTES AND TOOLS
    # ------------------------------------------------------------

    def _get_user_input_domain(self, survey, line_filter_domain, **post):
        user_input_domain = ["&", ("test_entry", "=", False), ("survey_id", "=", survey.id)]
        if line_filter_domain:
            matching_line_ids = request.env["of.survey.user_input.line"].sudo().search(line_filter_domain).ids
            user_input_domain = expression.AND([[("user_input_line_ids", "in", matching_line_ids)], user_input_domain])
        if post.get("finished"):
            user_input_domain = expression.AND([[("state", "=", "done")], user_input_domain])
        else:
            user_input_domain = expression.AND([[("state", "!=", "new")], user_input_domain])
        return user_input_domain
