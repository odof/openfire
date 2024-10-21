# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import Form

from odoo.addons.of_equipment.tests.common import TestOFEquipmentCommon


@freeze_time("2024-11-28")
class TestOFCalendarEvent(TestOFEquipmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.event = self.env["calendar.event"].create(
            {
                "name": "Test Event 1",
                "of_type": "intervention",
                "start": fields.Datetime.now().replace(hour=8, minute=30, second=0),
                "stop": fields.Datetime.now().replace(hour=10, minute=30, second=0),
                "of_company_id": self.company_fr.id,
                "of_employee_id": self.employee_tech_johnny.id,
                "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                "of_partner_id": self.customer_johnny_crash.id,
                "of_use_equipment": True,
                "of_template_id": self.template_maintenance_equipment.id,
                "of_task_id": self.task_sweeping.id,
                "of_linked_equipment_ids": [
                    Command.create(
                        {
                            "equipment_id": self.equipment_wood_stove.id,
                        }
                    )
                ],
            },
        )
        self.survey = self.env["of.survey.survey"].create(
            {
                "title": "Test Survey",
                "question_ids": [
                    (
                        Command.create(
                            {
                                "title": "Test Question",
                                "description": "Test Description",
                                "question_type": "text_box",
                            }
                        )
                    )
                ],
            }
        )

    def test_01_report_of_has_at_least_one_equipment_link_survey(self):
        """Test that the report of the event has at least one equipment link survey."""

        # No survey linked to the equipment link yet, should return False
        self.assertFalse(self.event._report_of_has_at_least_one_equipment_link_survey())

        # Add a survey to the equipment link
        with Form(self.event.of_linked_equipment_ids[0]) as link:
            link.survey_id = self.survey

        self.assertTrue(self.event._report_of_has_at_least_one_equipment_link_survey())
