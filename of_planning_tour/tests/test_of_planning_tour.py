# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command, fields

from odoo.addons.of_planning_tour.tests.common import TestOFPlanningTourCommon


@freeze_time("2024-12-02 08:00:00")  # Monday
class TestOFPlanningTour(TestOFPlanningTourCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_event_obj = cls.env["calendar.event"]

    def setUp(self):
        super().setUp()
        dt_8am = fields.Datetime.now()
        dt_9am = fields.Datetime.now().replace(hour=9, minute=0)
        dt_10am = fields.Datetime.now().replace(hour=10, minute=0)
        dt_11am = fields.Datetime.now().replace(hour=11, minute=0)
        dt_12pm = fields.Datetime.now().replace(hour=12, minute=0)
        dt_1pm = fields.Datetime.now().replace(hour=13, minute=0)
        dt_2pm = fields.Datetime.now().replace(hour=14, minute=0)
        dt_3pm = fields.Datetime.now().replace(hour=15, minute=0)
        self.event1, self.event2, self.event3, self.event4 = self.calendar_event_obj.with_context(
            of_avoid_osrm_calls=True
        ).create(
            [
                {
                    "name": "Event1",
                    "of_type": "intervention",
                    "start": dt_10am,
                    "stop": dt_11am,
                    "of_partner_id": self.partner_antoine.id,
                    "of_task_id": self.task_sweeping.id,
                    "duration": 1,
                    "of_employee_id": self.employee_tech_jean.id,
                    "of_employee_ids": [Command.set([self.employee_tech_jean.id])],
                },
                {
                    "name": "Event2",
                    "of_type": "intervention",
                    "start": dt_11am,
                    "stop": dt_12pm,
                    "of_partner_id": self.partner_saif.id,
                    "of_task_id": self.task_sweeping.id,
                    "duration": 1,
                    "of_employee_id": self.employee_tech_jean.id,
                    "of_employee_ids": [Command.set([self.employee_tech_jean.id])],
                },
                {
                    "name": "Event3",
                    "of_type": "intervention",
                    "start": dt_8am,
                    "stop": dt_9am,
                    "of_partner_id": self.partner_hounaida.id,
                    "of_task_id": self.task_sweeping.id,
                    "duration": 1,
                    "of_employee_id": self.employee_tech_jean.id,
                    "of_employee_ids": [Command.set([self.employee_tech_jean.id])],
                },
                {
                    "name": "Event4",
                    "of_type": "intervention",
                    "start": dt_1pm,
                    "stop": dt_3pm,
                    "of_partner_id": self.partner_hounaida.id,
                    "of_task_id": self.task_sweeping.id,
                    "duration": 2,
                    "of_employee_id": self.employee_tech_jean.id,
                    "of_employee_ids": [Command.set([self.employee_tech_jean.id])],
                },
            ]
        )

        self.bruce_event = self.env["calendar.event"].create(
            [
                {
                    "name": "Test Event 1",
                    "of_type": "intervention",
                    "start": dt_1pm.replace(minute=45, second=0),
                    "stop": dt_2pm.replace(minute=45, second=0),
                    "of_company_id": self.company_fr.id,
                    "of_employee_ids": [Command.set([self.employee_tech_bruce.id])],
                    "of_partner_id": self.customer_a.id,
                    "of_travel_duration": 0.0,
                },
            ]
        )

        self.bruce_tour = self.env["of.planning.tour"].search(
            [("employee_id", "=", self.employee_tech_bruce.id), ("date", "=", fields.Date.today())]
        )
        self.jean_tour = self.env["of.planning.tour"].search(
            [("employee_id", "=", self.employee_tech_jean.id), ("date", "=", fields.Date.today())]
        )

    def test_01_compute_line_data(self):
        """Checks the computation of the line data of a tour."""
        tour = self.planning_tour_obj.search(
            [("date", "=", fields.Date.today()), ("employee_id", "=", self.employee_tech_jean.id)], limit=1
        )
        self.assertEqual(len(tour), 1)
        self.assertEqual(len(tour.tour_line_ids), 4)

        tour.mapped("tour_line_ids")._compute_line_data()

        # Lines are sorted by sequence (Event3, Event1, Event2, Event4)
        line1, line2, line3, line4 = tour.tour_line_ids.sorted(key=lambda x: x.sequence)
        self.assertEqual(tour.tour_line_ids, line1 | line2 | line3 | line4)

        # Event3 is the first event of the day
        self.assertEqual(line1.intervention_id, self.event3)
        self.assertEqual(line1.previous_geo_lat, tour.start_address_id.partner_latitude)
        self.assertEqual(line1.previous_geo_lng, tour.start_address_id.partner_longitude)
        self.assertEqual(line1.next_geo_lat, line2.geo_lat)
        self.assertEqual(line1.next_geo_lng, line2.geo_lng)
        self.assertTrue(line1.is_first_line_of_tour)
        self.assertFalse(line1.is_last_line_of_tour)

        # Event1 is the second event of the day
        self.assertEqual(line2.intervention_id, self.event1)
        self.assertEqual(line2.previous_geo_lat, line1.geo_lat)
        self.assertEqual(line2.previous_geo_lng, line1.geo_lng)
        self.assertEqual(line2.next_geo_lat, line3.geo_lat)
        self.assertEqual(line2.next_geo_lng, line3.geo_lng)
        self.assertFalse(line2.is_first_line_of_tour)
        self.assertFalse(line2.is_last_line_of_tour)

        # Event2 is the third event of the day
        self.assertEqual(line3.intervention_id, self.event2)
        self.assertEqual(line3.previous_geo_lat, line2.geo_lat)
        self.assertEqual(line3.previous_geo_lng, line2.geo_lng)
        self.assertEqual(line3.next_geo_lat, line4.geo_lat)
        self.assertEqual(line3.next_geo_lng, line4.geo_lng)
        self.assertFalse(line3.is_first_line_of_tour)
        self.assertFalse(line3.is_last_line_of_tour)

        # Event4 is the last event of the day
        self.assertEqual(line4.intervention_id, self.event4)
        self.assertEqual(line4.previous_geo_lat, line3.geo_lat)
        self.assertEqual(line4.previous_geo_lng, line3.geo_lng)
        self.assertEqual(line4.next_geo_lat, tour.return_address_id.partner_latitude)
        self.assertEqual(line4.next_geo_lng, tour.return_address_id.partner_longitude)
        self.assertFalse(line4.is_first_line_of_tour)
        self.assertTrue(line4.is_last_line_of_tour)

    def test_02_tour_created(self):
        """Check that when a intervention is created, a tour, a tour line and available slots are created."""
        self.assertEqual(len(self.bruce_tour), 1)
        self.assertTrue(self.bruce_event in self.bruce_tour.mapped("tour_line_ids.intervention_id"))
        self.assertEqual(len(self.bruce_tour.available_slot_ids), 3)
        self.assertEqual(
            self.bruce_tour.available_slot_ids[0].start,
            fields.Datetime.now().replace(hour=7, minute=0, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[0].stop,
            fields.Datetime.now().replace(hour=11, minute=00, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[1].start,
            fields.Datetime.now().replace(hour=12, minute=0, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[1].stop,
            fields.Datetime.now().replace(hour=13, minute=45, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[2].start,
            fields.Datetime.now().replace(hour=14, minute=45, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[2].stop,
            fields.Datetime.now().replace(hour=16, minute=0, second=0),
        )

    def test_03_travel_duration_changed(self):
        """Check that when a the travel duration is changed, available slots are correctly updated."""

        # As Bruce has an event there is now 3 available slots (7-11, 12-13:45, 14:45-16 UTC)
        # If we increase the travel duration to 2 hours, the available slots should be reorganized
        self.bruce_event.of_travel_duration = 2.0
        self.bruce_tour._reorganize_available_slot()

        # Now there are only 2 available slots (7-11, 14:45-16 UTC)
        self.assertEqual(len(self.bruce_tour.available_slot_ids), 2)

        self.assertEqual(
            self.bruce_tour.available_slot_ids[0].start,
            fields.Datetime.now().replace(hour=7, minute=0, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[0].stop,
            fields.Datetime.now().replace(hour=11, minute=0, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[1].start,
            fields.Datetime.now().replace(hour=14, minute=45, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[1].stop,
            fields.Datetime.now().replace(hour=16, minute=0, second=0),
        )

    def test_04_unlink_event(self):
        """Check that when a the sole event of a tour is unlinked, the tour is correctly reset."""
        self.bruce_event.unlink()

        self.assertEqual(len(self.bruce_tour.tour_line_ids), 0)
        self.assertEqual(len(self.bruce_tour.available_slot_ids), 2)
        self.assertEqual(
            self.bruce_tour.available_slot_ids[0].start,
            fields.Datetime.now().replace(hour=7, minute=0, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[0].stop,
            fields.Datetime.now().replace(hour=11, minute=0, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[1].start,
            fields.Datetime.now().replace(hour=12, minute=0, second=0),
        )
        self.assertEqual(
            self.bruce_tour.available_slot_ids[1].stop,
            fields.Datetime.now().replace(hour=16, minute=0, second=0),
        )

    def test_05_compute_geo_data(self):
        """Check that the coordinates are correctly computed."""
        line1, line2, line3, line4 = self.jean_tour.tour_line_ids.sorted(key=lambda x: x.sequence)
        map_tour_line_coordinates = (
            f"{round(self.jean_tour.start_address_id.partner_longitude, 7)},"  # noqa
            f"{round(self.jean_tour.start_address_id.partner_latitude, 7)};"  # noqa
            f"{round(line1.geo_lng, 7)},{round(line1.geo_lat, 7)};"  # noqa
            f"{round(line2.geo_lng, 7)},{round(line2.geo_lat, 7)};"  # noqa
            f"{round(line3.geo_lng, 7)},{round(line3.geo_lat, 7)};"  # noqa
            f"{round(line4.geo_lng, 7)},{round(line4.geo_lat, 7)};"  # noqa
            f"{round(self.jean_tour.return_address_id.partner_longitude, 7)},"  # noqa
            f"{round(self.jean_tour.return_address_id.partner_latitude, 7)}"
        )
        self.assertEqual(self.jean_tour.map_tour_line_coordinates, map_tour_line_coordinates)

    def test_06_day_period(self):
        """Check that day period is correctly computed."""
        self.task_sweeping.duration = 0.5
        self.assertEqual(self.bruce_tour.available_slot_ids[0].day_period, "morning")
        self.assertEqual(self.bruce_tour.available_slot_ids[1].day_period, "afternoon")
        self.assertEqual(self.bruce_tour.available_slot_ids[2].day_period, "afternoon")
