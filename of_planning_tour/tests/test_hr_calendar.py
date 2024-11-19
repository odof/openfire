# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command

from odoo.addons.of_account.tests.common import TestOFAccountCommon


@freeze_time("2024-12-02 08:00:00")  # Monday
class TestOFPlanningTourHRCalendar(TestOFAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Just limit the number of months for tour creation to 1 for this test
        cls.env["ir.config_parameter"].set_param("of.planning.tour.nbr_months_tour_creation", 1)

    def setUp(self):
        super().setUp()

        # Create a new employee
        self.new_employee = self.env["hr.employee"].create(
            {
                "name": "New Employee",
            }
        )

        # Pick a tour in the future and check the available slots in the following tests
        self.twelve_december_tour = self.env["of.planning.tour"].search(
            [("employee_id", "=", self.new_employee.id), ("date", "=", "2024-12-12")]
        )

    def test_01_hr_calendar_attendance_update(self):
        """Test the update of the available slots for a tour when the employee's calendar is updated."""

        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 2)
        self.assertEqual(
            self.twelve_december_tour.available_slot_ids.mapped("time_slot"),
            ["08:00 - 12:00", "13:00 - 17:00"],
        )

        # Update directly the employee's calendar attendance for Thursday afternoons
        thu_workday_afternoon = self.new_employee.resource_calendar_id.attendance_ids.filtered(
            lambda a: a.dayofweek == "3" and a.day_period == "afternoon" and not a.display_type
        )
        thu_workday_afternoon.write({"hour_from": 13, "hour_to": 16})

        # Check the available slots again for the same tour
        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 2)
        self.assertEqual(
            self.twelve_december_tour.available_slot_ids.mapped("time_slot"),
            ["08:00 - 12:00", "13:00 - 16:00"],
        )

        # Update through the calendar the employee's calendar attendance for Thursday afternoons
        self.new_employee.resource_calendar_id.write(
            {
                "attendance_ids": [
                    Command.update(
                        thu_workday_afternoon.id,
                        {
                            "hour_from": 14,
                            "hour_to": 18,
                        },
                    )
                ]
            }
        )

        # Check the available slots again for the same tour
        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 2)
        self.assertEqual(
            self.twelve_december_tour.available_slot_ids.mapped("time_slot"),
            ["08:00 - 12:00", "14:00 - 18:00"],
        )

    def test_02_calendar_attendance_unlink(self):
        """Test the unlinking of calendar attendance records and its effect on available slots.

        The available slots for the tour should be updated when the employee's calendar attendance is unlinked.
        """
        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 2)
        self.assertEqual(
            self.twelve_december_tour.available_slot_ids.mapped("time_slot"),
            ["08:00 - 12:00", "13:00 - 17:00"],
        )

        # Update the employee's calendar to work on Thursday afternoons
        thu_workday_afternoon = self.new_employee.resource_calendar_id.attendance_ids.filtered(
            lambda a: a.dayofweek == "3" and a.day_period == "afternoon" and not a.display_type
        )

        # Remove the Thursday afternoon workday by deleting the attendance directly
        thu_workday_afternoon.unlink()

        # Check the available slots again for the same tour
        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 1)
        self.assertEqual(
            self.twelve_december_tour.available_slot_ids.mapped("time_slot"),
            ["08:00 - 12:00"],
        )

        # Remove the Thursday afternoon workday by deleting the attendance through the calendar
        thu_workday_morning = self.new_employee.resource_calendar_id.attendance_ids.filtered(
            lambda a: a.dayofweek == "3" and a.day_period == "morning" and not a.display_type
        )
        self.new_employee.resource_calendar_id.write(
            {
                "attendance_ids": [
                    Command.unlink(thu_workday_morning.id),
                ]
            }
        )

        # Check the available slots again for the same tour
        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 0)

    def test_03_calendar_attendance_create(self):
        """Test the creation of calendar attendance records and its effect on available slots.

        The available slots for the tour should be updated when the employee's calendar attendance is created.
        """
        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 2)
        self.assertEqual(
            self.twelve_december_tour.available_slot_ids.mapped("time_slot"),
            ["08:00 - 12:00", "13:00 - 17:00"],
        )

        # Update the employee's calendar to work on Thursday afternoons
        self.new_employee.resource_calendar_id.write(
            {
                "attendance_ids": [
                    Command.update(
                        self.new_employee.resource_calendar_id.attendance_ids.filtered(
                            lambda a: a.dayofweek == "3" and a.day_period == "afternoon" and not a.display_type
                        ).id,
                        {
                            "hour_from": 13,
                            "hour_to": 15,
                        },
                    ),
                    Command.create(
                        {
                            "name": "Jeudi après-midi 2",
                            "dayofweek": "3",
                            "hour_from": 16,
                            "hour_to": 18,
                            "day_period": "afternoon",
                        }
                    ),
                ]
            }
        )

        # Check the available slots again for the same tour
        self.assertEqual(len(self.twelve_december_tour.available_slot_ids), 3)
        self.assertEqual(
            self.twelve_december_tour.available_slot_ids.mapped("time_slot"),
            ["08:00 - 12:00", "13:00 - 15:00", "16:00 - 18:00"],
        )
