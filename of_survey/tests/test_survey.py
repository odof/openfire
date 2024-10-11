# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from freezegun import freeze_time

from odoo import _, fields
from odoo.tests import tagged
from odoo.tests.common import users

from odoo.addons.of_survey.tests import common

logger = logging.getLogger(__name__)


@tagged("openfire_custom")
class TestSurveyInternals(common.TestSurveyCommon):
    @freeze_time("2020-02-15 18:00")
    def test_answer_display_name(self):
        """The "display_name" field in a survey.user_input.line is a computed field that will
        display the answer label for any type of question.
        Let us test the various question types."""

        questions = self._create_one_question_per_type()
        user_input = self._add_answer(self.survey, self.survey_user.partner_id)

        for question in questions:
            if question.question_type == "char_box":
                question_answer = self._add_answer_line(question, user_input, "Char box answer")
                self.assertEqual(question_answer.display_name, "Char box answer")
            elif question.question_type == "text_box":
                question_answer = self._add_answer_line(question, user_input, "Text box answer")
                self.assertEqual(question_answer.display_name, "Text box answer")
            elif question.question_type == "date":
                question_answer = self._add_answer_line(question, user_input, fields.Datetime.now())
                self.assertEqual(question_answer.display_name, "15/02/2020")
            elif question.question_type == "simple_choice":
                question_answer = self._add_answer_line(question, user_input, question.suggested_answer_ids[0].id)
                self.assertEqual(question_answer.display_name, "SChoice0")
            elif question.question_type == "multiple_choice":
                question_answer_1 = self._add_answer_line(question, user_input, question.suggested_answer_ids[0].id)
                self.assertEqual(question_answer_1.display_name, "MChoice0")
                question_answer_2 = self._add_answer_line(question, user_input, question.suggested_answer_ids[1].id)
                self.assertEqual(question_answer_2.display_name, "MChoice1")

    @users("survey_manager")
    def test_answer_validation_mandatory(self):
        """For each type of question check that mandatory questions correctly check for complete answers"""
        for question in self._create_one_question_per_type():
            self.assertDictEqual(question.validate_question(""), {question.id: "TestError"})

    @users("survey_manager")
    def test_answer_validation_date(self):
        question = self._add_question(
            self.page_0,
            "Q0",
            "date",
            validation_required=True,
            validation_min_date="2015-03-20",
            validation_max_date="2015-03-25",
            validation_error_msg="ValidationError",
        )

        self.assertEqual(question.validate_question("Is Alfred an answer ?"), {question.id: _("This is not a date")})

        self.assertEqual(question.validate_question("2015-03-19"), {question.id: "ValidationError"})

        self.assertEqual(question.validate_question("2015-03-26"), {question.id: "ValidationError"})

        self.assertEqual(question.validate_question("2015-03-25"), {})

    @users("survey_manager")
    def test_answer_validation_char_box_email(self):
        question = self._add_question(self.page_0, "Q0", "char_box", validation_email=True)

        self.assertEqual(
            question.validate_question("not an email"), {question.id: _("This answer must be an email address")}
        )

        self.assertEqual(question.validate_question("email@example.com"), {})

    @users("survey_manager")
    def test_answer_validation_char_box_length(self):
        question = self._add_question(
            self.page_0,
            "Q0",
            "char_box",
            validation_required=True,
            validation_length_min=2,
            validation_length_max=8,
            validation_error_msg="ValidationError",
        )

        self.assertEqual(question.validate_question("l"), {question.id: "ValidationError"})

        self.assertEqual(question.validate_question("waytoomuchlonganswer"), {question.id: "ValidationError"})

        self.assertEqual(question.validate_question("valid"), {})

    def test_get_pages_and_questions_to_show(self):
        """
        Tests the method `_get_pages_and_questions_to_show` - it takes a recordset of
        question.question from a of.survey.survey and returns a recordset without
        invalid conditional questions and pages without description

        Structure of the test survey:

        sequence    | type                          | trigger       | validity
        ----------------------------------------------------------------------
        1           | page, no description          | /             | X
        2           | text_box                      | trigger is 6  | X
        4           | simple_choice                 | /             | V
        5           | page, description             | /             | V
        6           | multiple_choice               | /             | V
        7           | multiple_choice, no answers   | /             | V
        8           | text_box                      | trigger is 6  | V
        10          | simple_choice                 | trigger is 7  | X
        11          | simple_choice, no answers     | trigger is 8  | X
        12          | text_box                      | trigger is 11 | X
        """

        my_survey = self.env["of.survey.survey"].create(
            {
                "title": "my_survey",
                "questions_layout": "page_per_question",
                "questions_selection": "all",
                "access_mode": "public",
            }
        )
        [
            page_without_description,
            text_box_1,
            _simple_choice_1,
            page_with_description,
            multiple_choice_1,
            multiple_choice_2,
            text_box_2,
            simple_choice_2,
            simple_choice_3,
            text_box_3,
        ] = self.env["of.survey.question"].create(
            [
                {
                    "title": "no desc",
                    "survey_id": my_survey.id,
                    "sequence": 1,
                    "question_type": False,
                    "is_page": True,
                    "description": False,
                },
                {
                    "title": "text_box with invalid trigger",
                    "survey_id": my_survey.id,
                    "sequence": 2,
                    "is_page": False,
                    "question_type": "simple_choice",
                },
                {
                    "title": "valid simple_choice",
                    "survey_id": my_survey.id,
                    "sequence": 4,
                    "is_page": False,
                    "question_type": "simple_choice",
                    "suggested_answer_ids": [(0, 0, {"value": "a"})],
                },
                {
                    "title": "with desc",
                    "survey_id": my_survey.id,
                    "sequence": 5,
                    "is_page": True,
                    "question_type": False,
                    "description": "This page has a description",
                },
                {
                    "title": "multiple choice not conditional",
                    "survey_id": my_survey.id,
                    "sequence": 6,
                    "is_page": False,
                    "question_type": "multiple_choice",
                    "suggested_answer_ids": [(0, 0, {"value": "a"})],
                },
                {
                    "title": "multiple_choice with no answers",
                    "survey_id": my_survey.id,
                    "sequence": 7,
                    "is_page": False,
                    "question_type": "multiple_choice",
                },
                {
                    "title": "text_box with valid trigger",
                    "survey_id": my_survey.id,
                    "sequence": 8,
                    "is_page": False,
                    "question_type": "text_box",
                },
                {
                    "title": "simple choice w/ invalid trigger (no suggested_answer_ids)",
                    "survey_id": my_survey.id,
                    "sequence": 10,
                    "is_page": False,
                    "question_type": "simple_choice",
                },
                {
                    "title": "text_box w/ invalid trigger (not a mcq)",
                    "survey_id": my_survey.id,
                    "sequence": 11,
                    "is_page": False,
                    "question_type": "simple_choice",
                    "suggested_answer_ids": False,
                },
                {
                    "title": "text_box w/ invalid trigger (suggested_answer_ids is False)",
                    "survey_id": my_survey.id,
                    "sequence": 12,
                    "is_page": False,
                    "question_type": "text_box",
                },
            ]
        )
        text_box_1.write(
            {
                "is_conditional": True,
                "conditional_questions": [
                    (
                        0,
                        0,
                        {
                            "triggering_question_id": multiple_choice_1.id,
                            "answer_ids": [(6, 0, [multiple_choice_1.suggested_answer_ids[0].id])],
                        },
                    )
                ],
            }
        )
        text_box_2.write(
            {
                "is_conditional": True,
                "conditional_questions": [
                    (
                        0,
                        0,
                        {
                            "triggering_question_id": multiple_choice_1.id,
                            "answer_ids": [(6, 0, [multiple_choice_1.suggested_answer_ids[0].id])],
                        },
                    )
                ],
            }
        )
        simple_choice_2.write(
            {
                "is_conditional": True,
                "conditional_questions": [
                    (
                        0,
                        0,
                        {
                            "triggering_question_id": multiple_choice_2.id,
                        },
                    )
                ],
            }
        )
        simple_choice_3.write(
            {
                "is_conditional": True,
                "conditional_questions": [(0, 0, {"triggering_question_id": text_box_2.id})],
            }
        )
        text_box_3.write(
            {
                "is_conditional": True,
                "conditional_questions": [(0, 0, {"triggering_question_id": simple_choice_3.id})],
            }
        )
        invalid_records = page_without_description + simple_choice_2 + simple_choice_3 + text_box_3
        question_and_page_ids = my_survey.question_and_page_ids
        returned_questions_and_pages = my_survey._get_pages_and_questions_to_show()
        self.assertEqual(question_and_page_ids - invalid_records, returned_questions_and_pages)

    def test_multicondition(self):
        """Test de multicondition sur les questions"""
        # création du questionnaire

        my_survey = self.env["of.survey.survey"].create(
            {
                "title": "my_survey",
                "questions_layout": "page_per_question",
                "questions_selection": "all",
                "access_mode": "public",
            }
        )

        # création de la première question

        q1 = self.env["of.survey.question"].create(
            {
                "title": "Question 1",
                "survey_id": my_survey.id,
                "sequence": 6,
                "is_page": False,
                "question_type": "multiple_choice",
                "suggested_answer_ids": [(0, 0, {"value": "a"}), (0, 0, {"value": "b"})],
            },
        )

        # création de la deuxième question

        q2 = self.env["of.survey.question"].create(
            {
                "title": "Question 2",
                "survey_id": my_survey.id,
                "sequence": 6,
                "is_page": False,
                "question_type": "multiple_choice",
                "suggested_answer_ids": [(0, 0, {"value": "c"}), (0, 0, {"value": "d"})],
            },
        )

        # Création de la troisième question
        # ajout de la condition sur la troisième question selon les réponses de la première question
        # ajout de la condition sur la troisième question selon les réponses de la deuxième question
        q3 = self.env["of.survey.question"].create(
            {
                "title": "Question 3",
                "survey_id": my_survey.id,
                "sequence": 6,
                "is_page": False,
                "question_type": "multiple_choice",
                "suggested_answer_ids": [(0, 0, {"value": "e"}), (0, 0, {"value": "f"})],
                "is_conditional": True,
                "conditional_questions": [
                    (
                        0,
                        0,
                        {
                            "triggering_question_id": q1.id,
                            "answer_ids": [(6, 0, [q1.suggested_answer_ids[0].id])],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "operator": "OR",
                            "triggering_question_id": q2.id,
                            "answer_ids": [(6, 0, [q2.suggested_answer_ids[0].id])],
                        },
                    ),
                ],
            },
        )

        # Création de la quatrième question
        # ajout de la condition sur la troisième question selon les réponses de la première question
        # ajout de la condition sur la troisième question selon les réponses de la deuxième question
        q4 = self.env["of.survey.question"].create(
            {
                "title": "Question 4",
                "survey_id": my_survey.id,
                "sequence": 6,
                "is_page": False,
                "question_type": "multiple_choice",
                "suggested_answer_ids": [(0, 0, {"value": "e"}), (0, 0, {"value": "f"})],
                "is_conditional": True,
                "conditional_questions": [
                    (
                        0,
                        0,
                        {
                            "triggering_question_id": q1.id,
                            "answer_ids": [(6, 0, [q1.suggested_answer_ids[0].id])],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "operator": "AND",
                            "triggering_question_id": q2.id,
                            "answer_ids": [(6, 0, [q2.suggested_answer_ids[0].id])],
                        },
                    ),
                ],
            },
        )

        # Création d'une réponse au questionnaire
        with self.with_user("survey_manager"):
            user_input = self.env["of.survey.user_input"].create(
                {
                    "survey_id": my_survey.id,
                    "state": "new",
                    "partner_id": self.env.user.partner_id.id,
                }
            )
            # réponse aux deux questions

            user_input.write(
                {
                    "user_input_line_ids": [
                        (
                            0,
                            0,
                            {
                                "question_id": q1.id,
                                "suggested_answer_id": q1.suggested_answer_ids[0].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": q2.id,
                                "suggested_answer_id": q2.suggested_answer_ids[0].id,
                            },
                        ),
                    ]
                }
            )

            # vérification que la condition est bonne
            self.assertEqual(q3.is_valid_condition(), True)
            # vérification que la troisième question s'affiche bien
            self.assertEqual(
                user_input.is_valid_question(q3),
                True,
                _("The condition of Q3 is not activated and should be"),
            )

            # vérification de la condition de la question 4
            self.assertEqual(q4.is_valid_condition(), True)
            # Vérification que la 4ème question s'affiche bien
            self.assertEqual(
                user_input.is_valid_question(q4),
                True,
                _("The condition of Q4 is not activated and should be"),
            )

            # On crée des réponses qui ne doivent pas déclencher la question 4
            user_input = self.env["of.survey.user_input"].create(
                {
                    "survey_id": my_survey.id,
                    "state": "new",
                    "partner_id": self.env.user.partner_id.id,
                }
            )

            user_input.write(
                {
                    "user_input_line_ids": [
                        (
                            0,
                            0,
                            {
                                "question_id": q1.id,
                                "suggested_answer_id": q1.suggested_answer_ids[0].id,
                            },
                        ),
                    ]
                }
            )

            # vérification de la condition de la question 4
            self.assertEqual(q4.is_valid_condition(), True)
            # Vérification que la 4ème question s'affiche bien
            self.assertEqual(
                user_input.is_valid_question(q4),
                False,
                _("The condition of Q4 is activated and should not be"),
            )
