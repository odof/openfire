# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.of_equipment_service.tests.common import TestOFEquipmentServiceCommon


@freeze_time("2024-03-11")
class TestOFServiceRequest(TestOFEquipmentServiceCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Today (11/03/2024 07:00:00 UTC = 11/03/2024 08:00:00 Europe/Paris)
        cls.today_8am = fields.Datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)

        # Create a service request
        cls.service_request_with_equipments = (
            cls.env["of.service.request"]
            .with_context(ignore_equipment_ids_check=True)
            .create(
                {
                    "partner_id": cls.customer_johnny_crash.id,
                    "address_id": cls.customer_johnny_crash.id,
                    "task_id": cls.task_installation.id,
                    "duration": 1,
                    "type_id": cls.env.ref("of_service.of_service_request_type_installation").id,
                    "company_id": cls.company_fr.id,
                    "use_equipment": True,
                    "equipment_ids": [
                        Command.set(
                            [
                                cls.equipment_wood_stove_jc.id,
                                cls.equipment_wood_stove_jc_apt.id,
                                cls.equipment_wood_stove_jc_ch.id,
                                cls.equipment_wood_stove_jc_mh.id,
                                cls.equipment_ash_vacuum_cleaner_jc.id,
                            ]
                        )
                    ],
                    "employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                    "next_date": cls.today_8am.date(),
                    "end_date": cls.today_8am.date() + relativedelta(days=15),
                }
            )
        )

    def _form_create_intervention(
        self, start=None, stop=None, duration=1, name="Test Event", service_request=None, type_id=None
    ):
        """Helper method to create an intervention (through Form() proxy) with the given parameters and return it."""
        with Form(self.env["calendar.event"].with_context(ignore_equipment_ids_check=True)) as intervention_form:
            intervention_form.start = start or self.today_8am
            intervention_form.stop = stop or self.today_8am + relativedelta(hours=duration)
            intervention_form.duration = duration
            intervention_form.name = name
            intervention_form.of_partner_id = self.customer_johnny_crash
            if service_request:
                intervention_form.of_request_id = service_request
            if type_id:
                intervention_form.of_type_id = type_id
            intervention_form.of_use_equipment = True
            intervention_form.of_employee_ids.add(self.employee_tech_johnny)
            intervention_form.of_force_dates = True  # we don't care about events overlapping in this test
            if not intervention_form.of_task_id:
                intervention_form.of_task_id = self.task_installation
            intervention = intervention_form.save()
        return intervention

    def test_01_create_service_request_no_equipment(self):
        """Test the creation of a service request without equipment.
        That should raise an error as the use_equipment field is not True (equipment_ids is not visible)."""
        with Form(self.env["of.service.request"]) as request_form:
            request_form.partner_id = self.customer_johnny_crash
            request_form.address_id = self.customer_johnny_crash
            request_form.task_id = self.task_installation
            request_form.type_id = self.env.ref("of_service.of_service_request_type_installation")
            request_form.company_id = self.company_fr
            request_form.next_date = self.today_8am.date()
            request_form.end_date = self.today_8am.date() + relativedelta(days=15)
            with self.assertRaises(AssertionError) as create_service_request_error:  # use_equipment is False
                request_form.equipment_ids.add(self.equipment_wood_stove)
        self.assertEqual("field equipment_ids is not visible", create_service_request_error.exception.args[0])

    def test_02_create_service_request_equipment(self):
        # Create a service request
        service_request = self.env["of.service.request"].create(
            {
                "partner_id": self.customer_johnny_holiday.id,
                "address_id": self.customer_johnny_holiday.id,
                "task_id": self.task_installation.id,
                "type_id": self.env.ref("of_service.of_service_request_type_installation").id,
                "company_id": self.company_fr.id,
                "use_equipment": True,
                "next_date": self.today_8am.date(),
                "end_date": self.today_8am.date() + relativedelta(days=15),
            }
        )
        # Johny Holiday has only one equipment so equipment_ids should be filled automatically with it
        self.assertRecordValues(service_request.equipment_ids, [{"name": "JH/WS00001"}])

    def test_03_create_service_request_with_no_equipment(self):
        # Create a service request with no equipment
        with self.assertRaises(UserError) as error:
            self.env["of.service.request"].create(
                {
                    "partner_id": self.customer_johnny_crash.id,
                    "address_id": self.customer_johnny_crash.id,
                    "task_id": self.task_installation.id,
                    "type_id": self.env.ref("of_service.of_service_request_type_installation").id,
                    "company_id": self.company_fr.id,
                    "use_equipment": True,
                    "next_date": self.today_8am.date(),
                    "end_date": self.today_8am.date() + relativedelta(days=15),
                }
            )
            # Johny Crash has many equipment so equipment_ids should stay False
        self.assertEqual(error.exception.args[0], "Veuillez ajouter au moins un équipement")

    def test_04_create_service_request_manual_equipment(self):
        # Create a service request with one equipment manually
        service_request = self.env["of.service.request"].create(
            {
                "partner_id": self.customer_johnny_crash.id,
                "address_id": self.customer_johnny_crash.id,
                "task_id": self.task_installation.id,
                "type_id": self.env.ref("of_service.of_service_request_type_installation").id,
                "company_id": self.company_fr.id,
                "use_equipment": True,
                "equipment_ids": [Command.set([self.equipment_wood_stove_jc_ch.id])],
                "next_date": self.today_8am.date(),
                "end_date": self.today_8am.date() + relativedelta(days=15),
            }
        )
        self.assertRecordValues(service_request.equipment_ids, [{"name": "JC-CH/WS00004"}])

    def test_05_calendar_event_equipments_domain_with_request(self):
        """Test the domain of the equipment_ids field in the calendar event form when linked to a service request
        with equipments.

        The domain should be based on the related service request.
        First Intervention should have all equipments available.
        Second Intervention should have only the remaining equipments available.
        """
        # Check the service request with equipments
        self.assertEqual(len(self.service_request_with_equipments.equipment_ids), 5)
        self.assertEqual(len(self.service_request_with_equipments.intervention_ids), 0)

        # Create a calendar event with the service request
        intervention = self._form_create_intervention(
            start=self.today_8am,  # 8:00
            stop=self.today_8am + relativedelta(hour=9),  # 9:00
            duration=1,
            name="Test event Johnny Crash",
            service_request=self.service_request_with_equipments,
        )
        # Check equipments domain in the calendar event (should be all available here)
        self.assertEqual(len(intervention.of_equipment_ids_domain), 5)

        # Assign equipment to the intervention
        with Form(intervention) as intervention_form:
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_apt)
            intervention = intervention_form.save()

        # Create a second calendar event with the service request (should have only 3 available equipments)
        intervention2 = self._form_create_intervention(
            start=self.today_8am + relativedelta(hour=9, minute=30),  # 9:30
            stop=self.today_8am + relativedelta(hour=10, minute=30),  # 10:30
            duration=1.0,
            name="Test event 2 Johnny Crash",
            service_request=self.service_request_with_equipments,
        )
        self.assertEqual(len(intervention2.of_equipment_ids_domain), 3)

    def test_06_calendar_event_equipments_domain_without_request(self):
        """Test the domain of the equipment_ids field in the calendar event form when not linked to a service request.
        First Intervention should have all equipments available.
        Second Intervention should have all equipments available too because it's not linked to a service request.
        Third Intervention should have only 4 available equipments because we changed the address of an equipment.
        """
        # Create a calendar event without service request
        intervention = self._form_create_intervention(
            start=self.today_8am,  # 8:00
            stop=self.today_8am + relativedelta(hour=9),  # 9:00
            duration=1,
            name="Test event Johnny Crash",
            service_request=False,
        )

        # Check equipments domain in the calendar event (should be all available here)
        self.assertEqual(len(intervention.of_equipment_ids_domain), 5)

        # Assign equipment to the intervention
        with Form(intervention) as intervention_form:
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_apt)
            intervention = intervention_form.save()

        # Create a second calendar event without service request (should have all equipments available here too)
        intervention2 = self._form_create_intervention(
            start=self.today_8am + relativedelta(hour=10),  # 10:00
            stop=self.today_8am + relativedelta(hour=11),  # 11:00
            name="Test event 2 Johnny Crash",
            service_request=False,
        )
        self.assertEqual(len(intervention2.of_equipment_ids_domain), 5)

        # Create a third calendar event after changing the address of an equipment
        johnny_be_goode = self.env["res.partner"].create(
            {
                "name": "Johnny B. Goode",
                "street": "1 rue de Chuck Berry",
                "city": "Rennes",
                "zip": "35000",
            }
        )
        self.equipment_wood_stove_jc.write(
            {
                "customer_id": johnny_be_goode.id,
                "site_address_id": johnny_be_goode.id,
            }
        )
        intervention2._compute_equipment_ids_domain()
        self.assertEqual(len(intervention2.of_equipment_ids_domain), 4)

    def test_07_check_request_intervention_lines_modifying_event(self):
        """
        Test the creation of intervention lines when creating a service request with equipments and modifying equipments
        in the intervention.

        This test verifies the following steps:
        1. Checks the initial state of the service request with equipments.
        2. Creates a calendar event with the service request.
        3. Assigns equipment to the intervention.
        4. Checks the intervention lines of the service request.
        5. Removes an equipment from the intervention and checks the intervention lines again.
        6. Changes one equipment in the intervention and checks the intervention lines again.
        7. Creates a second calendar event with the service request and checks that only the remaining equipments
            are available in the domain.
        8. Removes the service request from the intervention and checks the intervention lines again.
        """
        # Check the service request with equipments
        self.assertEqual(len(self.service_request_with_equipments.equipment_ids), 5)
        self.assertEqual(len(self.service_request_with_equipments.intervention_ids), 0)

        # Create a calendar event with the service request
        intervention = self._form_create_intervention(
            start=self.today_8am,  # 8:00
            stop=self.today_8am + relativedelta(hour=9),  # 9:00
            duration=1,
            name="Test event Johnny Crash",
            service_request=self.service_request_with_equipments,
        )
        self.assertEqual(len(self.service_request_with_equipments.intervention_ids), 1)
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 0)

        # Assign equipment to the intervention
        with Form(intervention) as intervention_form:
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_apt)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_ch)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_mh)
            intervention_form.of_equipment_ids.add(self.equipment_ash_vacuum_cleaner_jc)
            intervention = intervention_form.save()

        # Check the intervention lines of the service request
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 5)
        self.assertRecordValues(
            self.service_request_with_equipments.equipment_intervention_ids,
            [
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_apt.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_ch.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
            ],
        )

        # Remove an equipment from the intervention and check the intervention lines again
        intervention.of_equipment_ids = [
            Command.set(
                [
                    self.equipment_wood_stove_jc_apt.id,
                    self.equipment_wood_stove_jc_mh.id,
                    self.equipment_wood_stove_jc_ch.id,
                    self.equipment_ash_vacuum_cleaner_jc.id,
                ]
            )
        ]
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 4)
        self.assertRecordValues(
            self.service_request_with_equipments.equipment_intervention_ids,
            [
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_apt.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_ch.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
            ],
        )

        # Change one equipment in the intervention and check the intervention lines again
        intervention.of_equipment_ids = [
            Command.set(
                [
                    self.equipment_wood_stove_jc.id,
                    self.equipment_wood_stove_jc_mh.id,
                    self.equipment_wood_stove_jc_ch.id,
                    self.equipment_ash_vacuum_cleaner_jc.id,
                ]
            )
        ]
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 4)
        self.assertRecordValues(
            self.service_request_with_equipments.equipment_intervention_ids,
            [
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_ch.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc.id},
            ],
        )

        # Create a second calendar event with the service request and check that only the remaining equipments
        # are available in the domain
        intervention2 = self._form_create_intervention(
            start=self.today_8am + relativedelta(hour=14),  # 14:00
            stop=self.today_8am + relativedelta(hour=15),  # 15:00
            duration=1,
            name="Test event 2 Johnny Crash",
            service_request=self.service_request_with_equipments,
        )
        self.assertEqual(len(intervention2.of_equipment_ids_domain), 1)

        # Remove the service request from the intervention and check the intervention lines again
        intervention.of_request_id = False
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 0)
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 0)

    def test_08_check_request_intervention_lines_modifying_request(self):
        """
        Test the creation of intervention lines when creating a service request with equipments and modifying equipments
        in the service request.

        This test verifies the following steps:
        1. Checks the initial state of the service request with equipments.
        2. Creates a calendar event with the service request.
        3. Assigns equipment to the intervention.
        4. Checks the intervention lines of the service request.
        5. Removes one equipment from the service request and checks the intervention lines again.
        """
        # Check the service request with equipments
        self.assertEqual(len(self.service_request_with_equipments.equipment_ids), 5)
        self.assertEqual(len(self.service_request_with_equipments.intervention_ids), 0)

        # Create a calendar event with the service request
        intervention = self._form_create_intervention(
            start=self.today_8am,  # 8:00
            stop=self.today_8am + relativedelta(hour=9),  # 9:00
            duration=1,
            name="Test event Johnny Crash",
            service_request=self.service_request_with_equipments,
        )
        self.assertEqual(len(self.service_request_with_equipments.intervention_ids), 1)
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 0)

        # Assign equipment to the intervention
        with Form(intervention) as intervention_form:
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_apt)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_ch)
            intervention_form.of_equipment_ids.add(self.equipment_wood_stove_jc_mh)
            intervention_form.of_equipment_ids.add(self.equipment_ash_vacuum_cleaner_jc)
            intervention = intervention_form.save()

        # Check the intervention lines of the service request
        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 5)

        # Remove one equipment from the service request and check the intervention lines again
        self.service_request_with_equipments.equipment_ids -= self.equipment_wood_stove_jc_apt

        self.assertEqual(len(self.service_request_with_equipments.equipment_intervention_ids), 4)
        self.assertRecordValues(
            self.service_request_with_equipments.equipment_intervention_ids,
            [
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_wood_stove_jc_ch.id},
                {"event_id": intervention.id, "equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
            ],
        )
