# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, fields

from odoo.addons.of_equipment.tests.common import TestOFEquipmentCommon


class TestOFCalendarEvent(TestOFEquipmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_compute_of_history_intervention_ids(self):
        """Test the _compute_of_history_intervention_ids method.
        Test Event 1, 2 and 3 are in the past and Test Event 4 is in the future.
        Test Event 2, 3 and 4 are linked to an equipment and Test Event 1 is not.
        Test Event 2 and 4 are linked to the same equipment.

        So the history of Test Event 4 should be Test Event 3 and Test Event 1 because they are in the past and
        Test Event 3 is linked to a different equipment than Test Event 4.
        """
        events = self.env["calendar.event"].create(
            [
                {
                    "name": "Test Event 1",
                    "of_type": "intervention",
                    "start": fields.Datetime.now().replace(hour=13, minute=30, second=0) - timedelta(days=1),
                    "stop": fields.Datetime.now().replace(hour=14, minute=30, second=0) - timedelta(days=1),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                    "of_partner_id": self.customer_a.id,
                },
                {
                    "name": "Test Event 2",
                    "of_type": "intervention",
                    "start": fields.Datetime.now().replace(hour=9, minute=30, second=0) - timedelta(days=1),
                    "stop": fields.Datetime.now().replace(hour=11, minute=30, second=0) - timedelta(days=1),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                    "of_partner_id": self.customer_a.id,
                    "of_use_equipment": True,
                    "of_equipment_ids": [Command.set([self.equipment_wood_stove.id])],
                },
                {
                    "name": "Test Event 3",
                    "of_type": "intervention",
                    "start": fields.Datetime.now().replace(hour=14, minute=30, second=0) - timedelta(days=1),
                    "stop": fields.Datetime.now().replace(hour=15, minute=30, second=0) - timedelta(days=1),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                    "of_partner_id": self.customer_a.id,
                    "of_use_equipment": True,
                    "of_equipment_ids": [Command.set([self.equipment_ash_vacuum_cleaner.id])],
                },
                {
                    "name": "Test Event 4",
                    "of_type": "intervention",
                    "start": fields.Datetime.now().replace(minute=0, second=0),
                    "stop": fields.Datetime.now() + timedelta(hours=1),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                    "of_partner_id": self.customer_a.id,
                    "of_use_equipment": True,
                    "of_equipment_ids": [Command.set([self.equipment_wood_stove.id])],
                },
            ]
        )
        last_event = events[-1]
        last_event._compute_of_history_intervention_ids()
        self.assertEqual(len(last_event.of_history_intervention_ids), 2)
        self.assertRecordValues(
            last_event.of_history_intervention_ids,
            [
                {"name": "Test Event 3", "of_equipment_ids": [self.equipment_ash_vacuum_cleaner.id]},
                {"name": "Test Event 1", "of_equipment_ids": []},
            ],
        )

    def test_02_compute_of_history_equipment_ids(self):
        """Test the _compute_of_history_equipment_ids method.
        Test Event 1, 2, 3 and 4 are linked to an equipment. Test Event 1 is the most recent and Test Event 4 is the
        oldest. Test Event 2 and 3 are in between.

        So the history of Test Event 1 should be Test Event 2, 3 and 4.
        """
        now = fields.Datetime.now()
        # Create a calendar event with an equipment
        event1 = self.env["calendar.event"].create(
            {
                "name": "Test Event 1",
                "of_type": "intervention",
                "start": now,
                "stop": now + timedelta(hours=1),
                "of_company_id": self.company_fr.id,
                "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                "of_partner_id": self.customer_a.id,
                "of_use_equipment": True,
                "of_equipment_ids": [Command.set([self.equipment_wood_stove.id])],
            }
        )

        # Create multiple intervention records for the equipment with different start dates
        event2, event3, event4 = self.env["calendar.event"].create(
            [
                {
                    "name": "Test Event 2",
                    "of_type": "intervention",
                    "start": event1.start - timedelta(days=1),
                    "stop": event1.stop - timedelta(days=1),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                    "of_partner_id": self.customer_a.id,
                    "of_use_equipment": True,
                    "of_equipment_ids": [Command.set([self.equipment_wood_stove.id])],
                },
                {
                    "name": "Test Event 3",
                    "of_type": "intervention",
                    "start": event1.start - timedelta(days=2),
                    "stop": event1.stop - timedelta(days=2),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                    "of_partner_id": self.customer_a.id,
                    "of_use_equipment": True,
                    "of_equipment_ids": [Command.set([self.equipment_wood_stove.id])],
                },
                {
                    "name": "Test Event 4",
                    "of_type": "intervention",
                    "start": event1.start - timedelta(days=3),
                    "stop": event1.stop - timedelta(days=3),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                    "of_partner_id": self.customer_a.id,
                    "of_use_equipment": True,
                    "of_equipment_ids": [Command.set([self.equipment_wood_stove.id])],
                },
            ]
        )

        event1._compute_of_history_equipment_ids()
        self.assertEqual(len(event1.of_history_equipment_ids), 3)
        self.assertRecordValues(
            event1.of_history_equipment_ids,
            [
                {"name": "Test Event 2", "start": event2.start},
                {"name": "Test Event 3", "start": event3.start},
                {"name": "Test Event 4", "start": event4.start},
            ],
        )
