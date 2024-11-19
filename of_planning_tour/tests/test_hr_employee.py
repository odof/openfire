# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields

from odoo.addons.of_account.tests.common import TestOFAccountCommon


@freeze_time("2024-12-02 08:00:00")  # Monday
class TestOFPlanningTourHrEmployee(TestOFAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_calendar_mon_thu_wed = cls.env["resource.calendar"].create(
            {
                "name": "Custom (lundi AM/PM, mardi AM/PM, mercredi AM/PM)",
                "attendance_ids": [
                    Command.create(
                        {
                            "name": "Lundi matin",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    Command.create(
                        {
                            "name": "Lundi après-midi",
                            "dayofweek": "0",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    Command.create(
                        {
                            "name": "Mardi matin",
                            "dayofweek": "1",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    Command.create(
                        {
                            "name": "Mardi après-midi",
                            "dayofweek": "1",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    Command.create(
                        {
                            "name": "Mercredi matin",
                            "dayofweek": "2",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    Command.create(
                        {
                            "name": "Mercredi après-midi",
                            "dayofweek": "2",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                ],
            }
        )

    def setUp(self):
        super().setUp()

    def test_01_employee_tour_create(self):
        """Test the creation of employee tours based on the configuration parameter for the number of months."""
        hr_employee_obj = self.env["hr.employee"]
        now = fields.Datetime.now()

        # Ensure the number of months for tour creation is 2 for this test
        self.env["ir.config_parameter"].set_param("of.planning.tour.nbr_months_tour_creation", 2)

        # Create a new employee
        new_employee = self.env["hr.employee"].create(
            {
                "name": "New Employee",
            }
        )
        in_two_months = now + relativedelta(months=2)

        employee_work_days = new_employee._get_employee_work_days()[new_employee.id]
        tour_dates = hr_employee_obj._get_tour_dates_from_work_days(
            start_date=now, days_count=(in_two_months - now).days, work_days=employee_work_days
        )
        # 45 working days in 2 months, from now (2024-12-02) to 2025-02-02
        self.assertEqual(len(tour_dates), 45)

        tours = self.env["of.planning.tour"].search([("employee_id", "=", new_employee.id)])
        self.assertEqual(len(tours), 45)

        # Change the number of months for tour creation
        self.env["ir.config_parameter"].set_param("of.planning.tour.nbr_months_tour_creation", 3)

        # Create another new employee
        new_employee2 = self.env["hr.employee"].create(
            {
                "name": "New Employee 2",
            }
        )
        in_three_months = now + relativedelta(months=3)

        employee_work_days = new_employee2._get_employee_work_days()[new_employee2.id]
        tour_dates = hr_employee_obj._get_tour_dates_from_work_days(
            start_date=now, days_count=(in_three_months - now).days, work_days=employee_work_days
        )
        # 65 working days in 3 months, from now (2024-12-02) to 2025-03-02
        self.assertEqual(len(tour_dates), 65)

        tours = self.env["of.planning.tour"].search([("employee_id", "=", new_employee2.id)])
        self.assertEqual(len(tours), 65)

    def test_02_employee_calendar_change(self):
        """Test the re-computation of tours when an employee's calendar is changed."""
        hr_employee_obj = self.env["hr.employee"]
        now = fields.Datetime.now()

        # Ensure the number of months for tour creation is 2 for this test
        self.env["ir.config_parameter"].set_param("of.planning.tour.nbr_months_tour_creation", 2)

        # Create a new employee
        new_employee = self.env["hr.employee"].create(
            {
                "name": "New Employee",
            }
        )
        in_two_months = now + relativedelta(months=2)

        employee_work_days = new_employee._get_employee_work_days()[new_employee.id]
        tour_dates = hr_employee_obj._get_tour_dates_from_work_days(
            start_date=now, days_count=(in_two_months - now).days, work_days=employee_work_days
        )
        # 45 working days in 2 months, from now (2024-12-02) to 2025-02-02
        self.assertEqual(len(tour_dates), 45)

        tours = self.env["of.planning.tour"].search([("employee_id", "=", new_employee.id)])
        self.assertEqual(len(tours), 45)

        # Update the employee's calendar
        new_employee.write({"resource_calendar_id": self.new_calendar_mon_thu_wed.id})

        tours = self.env["of.planning.tour"].search([("employee_id", "=", new_employee.id)])

        new_employee_work_days = new_employee._get_employee_work_days()[new_employee.id]
        new_tour_dates = hr_employee_obj._get_tour_dates_from_work_days(
            start_date=now, days_count=(in_two_months - now).days, work_days=new_employee_work_days
        )
        # 27 working days in 2 months (only Monday, Tuesday, Wednesday), from now (2024-12-02) to 2025-02-02
        self.assertEqual(len(new_tour_dates), 27)

        tours = self.env["of.planning.tour"].search([("employee_id", "=", new_employee.id)])
        self.assertEqual(len(tours), 27)
