# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command

from odoo.addons.of_planning_tour.tests.common import TestOFPlanningTourCommon

from .common import SAINT_GREGOIRE_VICTORIA_LAT_LNG


class TestOFPlanningTourCalendarEvent(TestOFPlanningTourCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()

    def _get_event_default_values(self):
        return {
            "name": "Event",
            "of_type": "intervention",
            "of_partner_id": self.partner_antoine.id,
            "of_task_id": self.task_sweeping.id,
            "of_company_id": self.company_fr.id,
            "of_employee_id": self.employee_tech_johnny.id,
            "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
            "start": self.now_dt_8am,
            "stop": self.now_dt_9am,
            "duration": 1,
        }

    def test_10_create_tour(self):
        """
        Test case for creating a tour when an event is created.
        """
        tour = self.planning_tour_obj.search(
            [("date", "=", self.now_dt.date()), ("employee_id", "=", self.employee_tech_johnny.id)]
        )
        self.assertEqual(tour, self.planning_tour_obj.browse())

        event = self.calendar_obj.with_context(of_avoid_tour_process=True, of_force_tour_creation=True).create(
            self._get_event_default_values()
        )
        event._compute_of_tour_ids()

        tour = self.planning_tour_obj.search(
            [("date", "=", self.now_dt.date()), ("employee_id", "=", self.employee_tech_johnny.id)]
        )

        self.assertEqual(len(tour), 1)
        self.assertEqual(len(tour.intervention_ids), 1)

        self.assertEqual(tour.intervention_ids, event)

    def test_11_handle_tour_update_geodata(self):
        """Test case for updating the geodata of the tour lines when the address of the partner is changed."""
        event = self.calendar_obj.with_context().create(self._get_event_default_values())
        event._compute_of_tour_ids()
        tour = event.of_tour_ids[0]
        first_line = tour.tour_line_ids[0]

        self.assertEqual(round(first_line.geo_lat, 7), self.partner_antoine.partner_latitude)
        self.assertEqual(round(first_line.geo_lng, 7), self.partner_antoine.partner_longitude)

        # Change the address of the partner
        partner_latitude = float(SAINT_GREGOIRE_VICTORIA_LAT_LNG[0])
        partner_longitude = float(SAINT_GREGOIRE_VICTORIA_LAT_LNG[1])
        self.partner_antoine.write(
            {
                "street": "1 Rue de la Terre Victoria",
                "zip": "35760",
                "city": "Saint-Grégoire",
                "partner_latitude": partner_latitude,
                "partner_longitude": partner_longitude,
            }
        )

        self.assertEqual(round(first_line.geo_lat, 7), partner_latitude)
        self.assertEqual(round(first_line.geo_lng, 7), partner_longitude)

    def test_12_handle_tour_update_hours(self):
        """Test case for updating the hours/sequence of the tour lines when the hours of the event are changed."""
        default_event_values = self._get_event_default_values()
        event1, event2 = self.calendar_obj.create(
            [
                default_event_values | {"name": "Event 1"},
                default_event_values
                | {
                    "name": "Event 2",
                    "start": self.now_dt.replace(hour=11, minute=0),
                    "stop": self.now_dt.replace(hour=12, minute=30),
                    "of_partner_id": self.partner_guillaume.id,
                },
            ]
        )

        (event1 + event2)._compute_of_tour_ids()
        tour = event1.of_tour_ids[0]

        # Check the tour and the tour lines
        self.assertEqual(tour, event2.of_tour_ids[0])
        self.assertEqual(len(tour.tour_line_ids), 2)
        self.assertEqual(tour.tour_line_ids[0].intervention_id, event1)
        self.assertEqual(tour.tour_line_ids[1].intervention_id, event2)
        self.assertEqual(tour.tour_line_ids[0].sequence, 1)
        self.assertEqual(tour.tour_line_ids[1].sequence, 2)

        # Change the hours of the first event
        event1.write({"start": self.now_dt.replace(hour=13, minute=0)})

        # First event should be the second in the tour
        self.assertEqual(len(tour.tour_line_ids), 2)
        self.assertEqual(tour.tour_line_ids[0].sequence, 2)
        self.assertEqual(tour.tour_line_ids[1].sequence, 1)
        self.assertEqual(tour.map_tour_line_ids[0].intervention_id, event2)
        self.assertEqual(tour.map_tour_line_ids[1].intervention_id, event1)

    def test_13_handle_tour_update_start_date(self):
        """Checks that an event is moved to another tour when its start date is changed."""
        default_event_values = self._get_event_default_values()

        event1, event2 = self.calendar_obj.create(
            [
                default_event_values
                | {
                    "name": "Event 1",
                    "stop": self.now_dt.replace(hour=11, minute=30),
                    "duration": 3.5,
                    "of_partner_id": self.partner_guillaume.id,
                },
                default_event_values
                | {
                    "name": "Event 2",
                    "start": self.now_dt.replace(hour=13, minute=0),
                    "stop": self.now_dt.replace(hour=15, minute=30),
                    "duration": 2.5,
                    "of_partner_id": self.partner_hounaida.id,
                },
            ]
        )
        (event1 + event2)._compute_of_tour_ids()
        tour = event1.of_tour_ids[0]
        self.assertEqual(tour, event2.of_tour_ids[0])
        self.assertEqual(len(tour.tour_line_ids), 2)

        # Change start date of the second event
        new_start = self.now_dt_10am + timedelta(days=1)
        event2.write({"start": new_start})
        event2._compute_of_tour_ids()

        self.assertEqual(len(tour.tour_line_ids), 1)
        self.assertNotEqual(event2.of_tour_ids, event1.of_tour_ids)

        tours = self.planning_tour_obj.search([("employee_id", "=", self.employee_tech_johnny.id)], order="date desc")
        self.assertEqual(len(tours), 2)
        self.assertEqual(
            tours.mapped("date"),
            [
                new_start.date(),
                self.now_dt.date(),
            ],
        )

    def test_14_handle_tour_update_cancelled(self):
        """Checks that a tour line is removed when the event is cancelled."""
        event = self.calendar_obj.create(self._get_event_default_values())
        event._compute_of_tour_ids()
        tour = event.of_tour_ids[0]
        self.assertEqual(len(tour.tour_line_ids), 1)

        # Cancel the event
        event.action_button_cancel()
        event._compute_of_tour_ids()

        self.assertEqual(len(tour.tour_line_ids), 0)

    def test_15_handle_tour_update_reoppened(self):
        """Checks that a tour line is added when the event is reopened."""
        event = self.calendar_obj.create(self._get_event_default_values())
        event._compute_of_tour_ids()
        tour = event.of_tour_ids[0]
        self.assertEqual(len(tour.tour_line_ids), 1)

        # Cancel the event
        event.action_button_cancel()
        self.assertEqual(len(tour.tour_line_ids), 0)

        # Reopen the event
        event.action_button_draft()
        self.assertEqual(len(tour.tour_line_ids), 1)

    def test_16_handle_tour_update_postponed(self):
        """Checks that a tour line is removed when the event is postponed and added when the event is reoppened."""
        event = self.calendar_obj.create(self._get_event_default_values())
        event._compute_of_tour_ids()
        tour = event.of_tour_ids[0]
        self.assertEqual(len(tour.tour_line_ids), 1)

        # Cancel the event
        event.action_button_postponed()
        self.assertEqual(len(tour.tour_line_ids), 0)

        # Reopen the event
        event.action_button_ongoing()
        self.assertEqual(len(tour.tour_line_ids), 1)

    def test_17_handle_tour_update_employee(self):
        """Checks that the tour line is removed from the previous tour and added to the new one when the
        employee is changed."""
        bruce_tour = self.planning_tour_obj.search(
            [("date", "=", self.now_dt.date()), ("employee_id", "=", self.employee_tech_bruce.id)]
        )
        self.assertEqual(bruce_tour, self.planning_tour_obj.browse())
        event = self.calendar_obj.create(self._get_event_default_values())

        event._compute_of_tour_ids()
        tour = event.of_tour_ids[0]
        self.assertEqual(len(tour.tour_line_ids), 1)

        # Change the employee of the event
        event.write(
            {
                "of_employee_id": self.employee_tech_bruce.id,
                "of_employee_ids": [Command.set([self.employee_tech_bruce.id])],
            }
        )

        self.assertEqual(len(tour.tour_line_ids), 0)

        bruce_tour = self.planning_tour_obj.search(
            [("date", "=", self.now_dt.date()), ("employee_id", "=", self.employee_tech_bruce.id)]
        )
        self.assertEqual(len(bruce_tour), 1)
        self.assertEqual(len(bruce_tour.tour_line_ids), 1)
        self.assertEqual(bruce_tour.tour_line_ids[0].intervention_id, event)
