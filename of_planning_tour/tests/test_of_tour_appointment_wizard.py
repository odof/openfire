# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, fields

from odoo.addons.of_planning_tour.tests.common import TestOFPlanningTourCommon

LATITUDE_SAINT_GREGOIRE_KERGUELEN = "48.1518877"
LONGITUDE_SAINT_GREGOIRE_KERGUELEN = "-1.6984516"


class TestOFTourAppointmentWizard(TestOFPlanningTourCommon):
    def setUp(self):
        super().setUp()

        self.search_mode = self.tour_appointment_wizard_obj._default_search_mode()
        self.search_type = self.tour_appointment_wizard_obj._default_search_type()

        self.company_fr.partner_id.write(
            {
                "street": "13 Rue des îles Kerguelen",
                "zip": "35760",
                "city": "Saint-Grégoire",
                "partner_latitude": LATITUDE_SAINT_GREGOIRE_KERGUELEN,
                "partner_longitude": LONGITUDE_SAINT_GREGOIRE_KERGUELEN,
                "of_geocoding_state": "success",
            }
        )

        self.service_request = self.env["of.service.request"].create(
            {
                "partner_id": self.partner_antoine.id,
                "address_id": self.partner_antoine.id,
                "template_id": self.template_sweeping.id,
                "task_id": self.task_sweeping.id,
                "type_id": self.env.ref("of_service.of_service_request_type_technical").id,
                "company_id": self.company_fr.id,
                "next_date": fields.Date.today(),
                "end_date": fields.Date.today() + timedelta(days=15),
                "employee_ids": [Command.set([self.employee_tech_jean.id])],
            }
        )

        self.event1, self.event2 = self.calendar_obj.with_context(of_avoid_osrm_calls=True).create(
            [
                {
                    "name": "Event1",
                    "of_type": "intervention",
                    "start": self.now_dt_8am,
                    "stop": self.now_dt_9am,
                    "of_partner_id": self.partner_hounaida.id,
                    "of_template_id": self.template_sweeping.id,
                    "of_task_id": self.task_sweeping.id,
                    "duration": 1,
                    "of_employee_id": self.employee_tech_jean.id,
                    "of_employee_ids": [Command.set([self.employee_tech_jean.id])],
                },
                {
                    "name": "Event2",
                    "of_type": "intervention",
                    "start": self.now_dt_12pm,
                    "stop": self.now_dt_1pm,
                    "of_partner_id": self.partner_saif.id,
                    "of_template_id": self.template_sweeping.id,
                    "of_task_id": self.task_sweeping.id,
                    "duration": 1,
                    "of_employee_id": self.employee_tech_jean.id,
                    "of_employee_ids": [Command.set([self.employee_tech_jean.id])],
                },
            ]
        )

        self.appointment_action = self.service_request.action_button_open_tour_appointment_wizard()
        self.appointment_wizard = self.tour_appointment_wizard_obj.browse(self.appointment_action["res_id"])
        self.tours = self.env["of.planning.tour"].search([("employee_id", "=", self.employee_tech_jean.id)])

    def test_01_default_values(self):
        """Check if the default values are correctly computed"""
        self.assertEqual(self.appointment_wizard.source_model, "of.service.request")
        self.assertEqual(self.appointment_wizard.partner_id, self.service_request.partner_id)
        self.assertEqual(self.appointment_wizard.pre_employee_ids, self.service_request.employee_ids)
        self.assertEqual(self.appointment_wizard.geo_lat, self.service_request.address_id.partner_latitude)
        self.assertEqual(self.appointment_wizard.geo_lng, self.service_request.address_id.partner_longitude)
        self.assertEqual(self.appointment_wizard.duration, self.service_request.template_id.task_id.duration)

    def test_02_config_settings(self):
        """Check if the default config values are correctly retrieved"""
        self.assertEqual(self.appointment_wizard.search_mode, self.search_mode)
        self.assertEqual(self.appointment_wizard.search_type, self.search_type)

    def test_03_action_button_search(self):
        """Check if the line_ids contains the same line as every by_*_line_ids"""
        self.assertEqual(
            self.appointment_wizard.mapped("line_ids.available_slot_id"), self.tours.mapped("available_slot_ids")
        )
        self.assertEqual(self.appointment_wizard.line_ids, self.appointment_wizard.by_distance_line_ids)
        self.assertEqual(self.appointment_wizard.line_ids, self.appointment_wizard.by_duration_line_ids)
        self.assertEqual(self.appointment_wizard.line_ids, self.appointment_wizard.by_date_line_ids)

    def test_04_distance_duration_date_sorted(self):
        """Check if the lines_ids are correctly sorted in every by_*_line_ids"""
        self.assertTrue(
            self.appointment_wizard.by_distance_line_ids[0].useful_distance
            <= self.appointment_wizard.by_distance_line_ids[1].useful_distance
        )
        self.assertTrue(
            self.appointment_wizard.by_duration_line_ids[0].useful_duration
            <= self.appointment_wizard.by_duration_line_ids[1].useful_duration
        )
        self.assertTrue(
            self.appointment_wizard.by_date_line_ids[0].date <= self.appointment_wizard.by_date_line_ids[1].date
        )

    def test_05_search_mode_button(self):
        """Check if the search type field is working correctly"""
        self.appointment_wizard.search_mode = "oneway"
        self.appointment_wizard.action_button_search()
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_duration, self.appointment_wizard.line_ids[0].previous_duration
        )
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_distance, self.appointment_wizard.line_ids[0].previous_distance
        )
        self.appointment_wizard.search_mode = "return"
        self.appointment_wizard.action_button_search()
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_duration, self.appointment_wizard.line_ids[0].next_duration
        )
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_distance, self.appointment_wizard.line_ids[0].next_distance
        )
        self.appointment_wizard.search_mode = "round_trip"
        self.appointment_wizard.action_button_search()
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_duration, self.appointment_wizard.line_ids[0].duration
        )
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_distance, self.appointment_wizard.line_ids[0].distance
        )
        self.appointment_wizard.search_mode = "oneway_or_return"
        self.appointment_wizard.action_button_search()
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_duration,
            min(
                self.appointment_wizard.line_ids[0].previous_duration,
                self.appointment_wizard.line_ids[0].next_duration,
            ),
        )
        self.assertEqual(
            self.appointment_wizard.line_ids[0].useful_distance,
            min(
                self.appointment_wizard.line_ids[0].previous_distance,
                self.appointment_wizard.line_ids[0].next_distance,
            ),
        )

    def test_06_compute_duration_str(self):
        """Check if the search type field is working correctly"""
        line_0 = self.appointment_wizard.line_ids[0]
        line_1 = self.appointment_wizard.line_ids[1]
        self.assertEqual(
            line_0.previous_duration_str,
            f"{int(line_0.previous_duration // 60):02d}:{int(line_0.previous_duration % 60):02d}",  # noqa E231
        )

        self.assertEqual(
            line_1.previous_duration_str,
            f"{int(line_1.previous_duration // 60):02d}:{int(line_1.previous_duration % 60):02d}",  # noqa E231
        )
