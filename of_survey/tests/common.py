# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import Counter

from odoo.tests import common

from odoo.addons.mail.tests.common import mail_new_test_user


class SurveyCase(common.TransactionCase):
    def setUp(self):
        super(SurveyCase, self).setUp()

        """ Some custom stuff to make the matching between questions and answers
          :param dict _type_match: dict
            key: question type
            value: (answer type, answer field_name)
        """
        self._type_match = {
            "text_box": ("text_box", "value_text_box"),
            "char_box": ("char_box", "value_char_box"),
            "date": ("date", "value_date"),
            "simple_choice": ("suggestion", "suggested_answer_id"),  # TDE: still unclear
            "multiple_choice": ("suggestion", "suggested_answer_id"),  # TDE: still unclear
        }

    # ------------------------------------------------------------
    # ASSERTS
    # ------------------------------------------------------------

    def assertAnswer(self, answer, state, page):
        self.assertEqual(answer.state, state)
        self.assertEqual(answer.last_displayed_page_id, page)

    def assertAnswerLines(self, page, answer, answer_data):
        """Check answer lines.

        :param dict answer_data:
          key = question ID
          value = {'value': [user input]}
        """
        lines = answer.user_input_line_ids.filtered(lambda line: line.page_id == page)
        answer_count = sum(len(user_input["value"]) for user_input in answer_data.values())
        self.assertEqual(len(lines), answer_count)
        for qid, user_input in answer_data.items():
            answer_lines = lines.filtered(lambda line: line.question_id.id == qid)
            question = answer_lines[0].question_id  # TDE note: might have several answers for a given question
            if question.question_type == "multiple_choice":
                values = user_input["value"]
                answer_fname = self._type_match[question.question_type][1]
                self.assertEqual(Counter(getattr(line, answer_fname).id for line in answer_lines), Counter(values))
            elif question.question_type == "simple_choice":
                [value] = user_input["value"]
                answer_fname = self._type_match[question.question_type][1]
                self.assertEqual(getattr(answer_lines, answer_fname).id, value)
            else:
                [value] = user_input["value"]
                answer_fname = self._type_match[question.question_type][1]
                self.assertEqual(getattr(answer_lines, answer_fname), value)

    def assertResponse(self, response, status_code, text_bits=None):
        self.assertEqual(response.status_code, status_code)
        for text in text_bits or []:
            self.assertIn(text, response.text)

    # ------------------------------------------------------------
    # DATA CREATION
    # ------------------------------------------------------------

    def _add_question(self, page, name, qtype, **kwargs):
        constr_mandatory = kwargs.pop("constr_mandatory", True)
        constr_error_msg = kwargs.pop("constr_error_msg", "TestError")

        sequence = kwargs.pop("sequence", False)
        if not sequence:
            sequence = page.question_ids[-1].sequence + 1 if page.question_ids else page.sequence + 1

        base_qvalues = {
            "sequence": sequence,
            "title": name,
            "question_type": qtype,
            "constr_mandatory": constr_mandatory,
            "constr_error_msg": constr_error_msg,
        }
        if qtype in ("simple_choice", "multiple_choice"):
            base_qvalues["suggested_answer_ids"] = [
                (
                    0,
                    0,
                    {
                        "value": label["value"],
                    },
                )
                for label in kwargs.pop("labels")
            ]
        else:
            pass
        base_qvalues.update(kwargs)
        question = self.env["of.survey.question"].create(base_qvalues)
        return question

    def _add_answer(self, survey, partner, **kwargs):
        base_avals = {
            "survey_id": survey.id,
            "partner_id": partner.id if partner else False,
            "email": kwargs.pop("email", False),
        }
        base_avals.update(kwargs)
        return self.env["of.survey.user_input"].create(base_avals)

    def _add_answer_line(self, question, answer, answer_value, **kwargs):
        qtype = self._type_match.get(question.question_type, (False, False))
        answer_type = kwargs.pop("answer_type", qtype[0])
        answer_fname = kwargs.pop("answer_fname", qtype[1])
        if question.question_type == "matrix":
            answer_fname = qtype[1][0]

        base_alvals = {
            "user_input_id": answer.id,
            "question_id": question.id,
            "skipped": False,
            "answer_type": answer_type,
        }
        base_alvals[answer_fname] = answer_value
        if "answer_value_row" in kwargs:
            answer_value_row = kwargs.pop("answer_value_row")
            base_alvals[qtype[1][1]] = answer_value_row

        base_alvals.update(kwargs)
        return self.env["of.survey.user_input.line"].create(base_alvals)

    # ------------------------------------------------------------
    # UTILS / CONTROLLER ENDPOINTS FLOWS
    # ------------------------------------------------------------

    def _access_start(self, survey):
        return self.url_open("/of_survey/start/%s" % survey.access_token)

    def _access_page(self, survey, token):
        return self.url_open("/of_survey/%s/%s" % (survey.access_token, token))

    def _access_begin(self, survey, token):
        url = survey.get_base_url() + "/of_survey/begin/%s/%s" % (survey.access_token, token)
        return self.opener.post(url=url, json={})

    def _access_submit(self, survey, token, post_data):
        url = survey.get_base_url() + "/of_survey/submit/%s/%s" % (survey.access_token, token)
        return self.opener.post(url=url, json={"params": post_data})

    def _find_csrf_token(self, text):
        csrf_token_re = re.compile('(input.+csrf_token.+value=")([a-f0-9]{40}o[0-9]*)', re.MULTILINE)
        return csrf_token_re.search(text).groups()[1]

    def _prepare_post_data(self, question, answers, post_data):
        values = answers if isinstance(answers, list) else [answers]
        if question.question_type == "multiple_choice":
            for value in values:
                value = str(value)
                if question.id in post_data:
                    if isinstance(post_data[question.id], list):
                        post_data[question.id].append(value)
                    else:
                        post_data[question.id] = [post_data[question.id], value]
                else:
                    post_data[question.id] = value
        else:
            [values] = values
            post_data[question.id] = str(values)
        return post_data

    def _answer_question(self, question, answer, answer_token, csrf_token, button_submit="next"):
        # Employee submits the question answer
        post_data = self._format_submission_data(
            question, answer, {"csrf_token": csrf_token, "token": answer_token, "button_submit": button_submit}
        )
        response = self._access_submit(question.survey_id, answer_token, post_data)
        self.assertResponse(response, 200)

        # Employee is redirected on next question
        response = self._access_page(question.survey_id, answer_token)
        self.assertResponse(response, 200)

    def _answer_page(self, page, answers, answer_token, csrf_token):
        post_data = {}
        for question, answer in answers.items():
            post_data[question.id] = answer.id
        post_data["page_id"] = page.id
        post_data["csrf_token"] = csrf_token
        post_data["token"] = answer_token
        response = self._access_submit(page.survey_id, answer_token, post_data)
        self.assertResponse(response, 200)
        response = self._access_page(page.survey_id, answer_token)
        self.assertResponse(response, 200)

    def _format_submission_data(self, question, answer, additional_post_data):
        post_data = {}
        post_data["question_id"] = question.id
        post_data.update(self._prepare_post_data(question, answer, post_data))
        if question.page_id:
            post_data["page_id"] = question.page_id.id
        post_data.update(**additional_post_data)
        return post_data

    # ------------------------------------------------------------
    # UTILS / TOOLS
    # ------------------------------------------------------------

    def _create_one_question_per_type(self):
        all_questions = self.env["of.survey.question"]
        for question_type, dummy in self.env["of.survey.question"]._fields["question_type"].selection:
            kwargs = {}
            if question_type == "multiple_choice":
                kwargs["labels"] = [{"value": "MChoice0"}, {"value": "MChoice1"}]
            elif question_type == "simple_choice":
                kwargs["labels"] = [{"value": "SChoice0"}, {"value": "SChoice1"}]
            all_questions |= self._add_question(self.page_0, "Q0", question_type, **kwargs)

        return all_questions


class TestSurveyCommon(SurveyCase):
    def setUp(self):
        super(TestSurveyCommon, self).setUp()

        """ Create test data: a survey with some pre-defined questions and various test users for ACL """
        self.survey_manager = mail_new_test_user(  # nosec : B106
            self.env,
            name="Gustave Doré",
            login="survey_manager",
            email="survey.manager@example.com",
            groups="of_survey.group_of_survey_manager,base.group_user",
            password="survey_manager",
        )  # nosec B106

        self.survey_user = mail_new_test_user(  # nosec : B106
            self.env,
            name="Lukas Peeters",
            login="survey_user",
            email="survey.user@example.com",
            groups="of_survey.group_of_survey_user,base.group_user",
            password="survey_user",
        )  # nosec B106

        self.user_emp = mail_new_test_user(  # nosec : B106
            self.env,
            name="Eglantine Employee",
            login="user_emp",
            email="employee@example.com",
            groups="base.group_user",
            password="user_emp",
        )  # nosec B106

        self.user_portal = mail_new_test_user(
            self.env, name="Patrick Portal", login="user_portal", email="portal@example.com", groups="base.group_portal"
        )

        self.user_public = mail_new_test_user(
            self.env, name="Pauline Public", login="user_public", email="public@example.com", groups="base.group_public"
        )

        self.customer = self.env["res.partner"].create(
            {
                "name": "Caroline Customer",
                "email": "customer@example.com",
            }
        )

        self.survey = (
            self.env["of.survey.survey"]
            .with_user(self.survey_manager)
            .create(
                {
                    "title": "Test Survey",
                    "access_mode": "public",
                    "users_login_required": True,
                    "users_can_go_back": False,
                }
            )
        )
        self.page_0 = (
            self.env["of.survey.question"]
            .with_user(self.survey_manager)
            .create(
                {
                    "title": "First page",
                    "survey_id": self.survey.id,
                    "sequence": 1,
                    "is_page": True,
                    "question_type": False,
                }
            )
        )
        self.question_ft = (
            self.env["of.survey.question"]
            .with_user(self.survey_manager)
            .create(
                {
                    "title": "Test Free Text",
                    "survey_id": self.survey.id,
                    "sequence": 2,
                    "question_type": "text_box",
                }
            )
        )
