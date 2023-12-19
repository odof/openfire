# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged('openfire_custom')
class TestPlanningSurvey(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.survey = cls.env['of.survey.survey'].create(
            {
                'title': 'Test Survey',
                'questions_layout': 'page_per_question',
                'questions_selection': 'all',
                'access_mode': 'public',
                'question_and_page_ids': [
                    Command.create(
                        {
                            'title': 'Question 1',
                            'sequence': 1,
                            'question_type': 'simple_choice',
                            'suggested_answer_ids': [
                                Command.create({'value': 'simple_choice_1'}),
                                Command.create({'value': 'simple_choice_2'}),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            'title': 'Question 2',
                            'sequence': 2,
                            'question_type': 'multiple_choice',
                            'suggested_answer_ids': [
                                Command.create({'value': 'multiple_choice_1'}),
                                Command.create({'value': 'multiple_choice_2'}),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            'title': 'Question 3',
                            'sequence': 3,
                            'question_type': 'text_box',
                        }
                    ),
                ],
            }
        )

    def test_01_event_survey_create(self):
        """Test that creating an event with a survey creates the questions."""
        event = self.env['calendar.event'].create(
            {
                'name': 'Test Event',
                'of_type': 'intervention',
                'of_survey_id': self.survey.id,
            }
        )
        self.assertEqual(event.of_survey_id, self.survey)
        self.assertEqual(len(event.of_question_ids), 3)
        self.assertRecordValues(
            event.of_question_ids,
            [
                {
                    'title': 'Question 1',
                    'sequence': 1,
                    'question_type': 'simple_choice',
                },
                {
                    'title': 'Question 2',
                    'sequence': 2,
                    'question_type': 'multiple_choice',
                },
                {'title': 'Question 3', 'sequence': 3, 'question_type': 'text_box'},
            ],
        )

    def test_02_event_survey_update(self):
        """Test that updating the survey of an event updates the questions. That should replace the questions."""
        event = self.env['calendar.event'].create(
            {
                'name': 'Test Event',
                'of_type': 'intervention',
                'of_survey_id': self.survey.id,
            }
        )
        new_survey = self.env['of.survey.survey'].create(
            {
                'title': 'New Survey',
                'questions_layout': 'page_per_question',
                'questions_selection': 'all',
                'access_mode': 'public',
                'question_and_page_ids': [
                    Command.create(
                        {
                            'title': 'New Question 1',
                            'sequence': 1,
                            'question_type': 'simple_choice',
                            'suggested_answer_ids': [
                                Command.create({'value': 'new_simple_choice_1'}),
                                Command.create({'value': 'new_simple_choice_2'}),
                            ],
                        }
                    )
                ],
            }
        )

        # Update the survey of the event
        event.of_survey_id = new_survey

        self.assertEqual(event.of_survey_id, new_survey)
        self.assertEqual(len(event.of_question_ids), 1)
        self.assertRecordValues(
            event.of_question_ids,
            [
                {
                    'title': 'New Question 1',
                    'sequence': 1,
                    'question_type': 'simple_choice',
                }
            ],
        )
