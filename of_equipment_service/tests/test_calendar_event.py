# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.of_equipment_service.tests.common import TestOFEquipmentServiceCommon


@freeze_time("2024-05-20")
class TestOFCalendarEvent(TestOFEquipmentServiceCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.today_8am = fields.Datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)

        # Create a service request with equipments
        cls.service_request_w_equipments = cls.env["of.service.request"].create(
            {
                "partner_id": cls.customer_johnny_crash.id,
                "address_id": cls.customer_johnny_crash.id,
                "type_id": cls.env.ref("of_service.of_service_request_type_installation").id,
                "template_id": cls.template_installation_equipment.id,
                "task_id": cls.task_installation.id,
                "duration": 8,
                "company_id": cls.company_fr.id,
                "use_equipment": True,
                "linked_equipment_ids": [
                    Command.create({"equipment_id": cls.equipment_wood_stove_jc.id}),
                    Command.create({"equipment_id": cls.equipment_ash_vacuum_cleaner_jc.id}),
                    Command.create({"equipment_id": cls.equipment_wood_stove_jc_apt.id}),
                    Command.create({"equipment_id": cls.equipment_wood_stove_jc_mh.id}),
                    Command.create({"equipment_id": cls.equipment_wood_stove_jc_ch.id}),
                ],
                "employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                "next_date": cls.today_8am.date(),
                "end_date": cls.today_8am.date() + relativedelta(days=15),
            }
        )

    def test_01_calendar_event_creation(self):
        """
        Test the creation of a calendar event from a service request with equipments.
        The event should have all the equipments linked to the service request and the equipment intervention lines
        should be created.
        """
        event = self._create_events_from_service_request(self.service_request_w_equipments)

        self.assertEqual(len(event), 1)

        equipments = (
            self.equipment_wood_stove_jc
            + self.equipment_ash_vacuum_cleaner_jc
            + self.equipment_wood_stove_jc_apt
            + self.equipment_wood_stove_jc_mh
            + self.equipment_wood_stove_jc_ch
        )
        self.assertEqual(event.of_equipment_ids, equipments)

        self.assertRecordValues(
            event.of_linked_equipment_ids,
            [
                {
                    "equipment_id": equipment.id,
                    "equipment_report_tmpl_id": self.eq_report_tmpl_maintenance.id,
                    "task_id": self.task_sweeping.id,  # task used on equipment intervention report template
                }
                for equipment in equipments
            ],
        )

        # The calender equipment links should have been created and linked to the service request equipment link
        for request_equipment_link in self.service_request_w_equipments.linked_equipment_ids:
            event_equipment_link = event.of_linked_equipment_ids.filtered(
                lambda lnk: lnk.request_link_id == request_equipment_link
            )
            self.assertTrue(event_equipment_link, "Event equipment link should exist for each request equipment link")
            self.assertEqual(
                request_equipment_link.equipment_id,
                event_equipment_link.equipment_id,
                "equipment_id should be the same between request equipment link and event equipment link",
            )

        # The equipment intervention lines should have been created
        self.assertRecordValues(
            self.service_request_w_equipments.equipment_intervention_ids,
            [
                {
                    "event_id": event.id,
                    "equipment_id": equipment.id,
                    "operator_id": self.employee_tech_johnny.id,
                    "start": self.today_8am,
                    "link_task_id": self.task_sweeping.id,
                    "state": "draft",
                }
                for equipment in equipments
            ],
        )

    def test_02_service_request_equipment_addition(self):
        """
        Test the addition of an equipment to a service request with equipments.

        The new added equipment shouldn't be propagated to the existing calendar event but should be available in the
        new event created after the addition.

        (Only when updating the service request from the form or directly from `of.service.request.write()`)
        """
        event = self._create_events_from_service_request(self.service_request_w_equipments)

        self.assertEqual(len(event), 1)

        equipments = (
            self.equipment_wood_stove_jc
            + self.equipment_ash_vacuum_cleaner_jc
            + self.equipment_wood_stove_jc_apt
            + self.equipment_wood_stove_jc_mh
            + self.equipment_wood_stove_jc_ch
        )
        self.assertEqual(event.of_equipment_ids, equipments)
        self.assertRecordValues(
            event.of_linked_equipment_ids,
            [
                {
                    "equipment_id": equipment.id,
                    "equipment_report_tmpl_id": self.eq_report_tmpl_maintenance.id,
                    "task_id": self.task_sweeping.id,
                }
                for equipment in equipments
            ],
        )

        with Form(self.service_request_w_equipments) as service_request_form:
            with service_request_form.linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = self.equipment_wood_stove_jh

        self.assertRecordValues(
            self.service_request_w_equipments.linked_equipment_ids,
            [
                {
                    "equipment_id": equipment.id,
                    "equipment_report_tmpl_id": self.eq_report_tmpl_maintenance.id,
                    "task_id": self.task_sweeping.id,
                }
                for equipment in equipments + self.equipment_wood_stove_jh
            ],
        )

        self.assertEqual(len(event.of_equipment_ids), 5)
        self.assertEqual(event.of_equipment_ids, equipments)
        self.assertRecordValues(
            event.of_linked_equipment_ids,
            [
                {
                    "equipment_id": equipment.id,
                    "equipment_report_tmpl_id": self.eq_report_tmpl_maintenance.id,
                    "task_id": self.task_sweeping.id,
                }
                for equipment in equipments
            ],
        )

        new_event = self._create_events_from_service_request(
            self.service_request_w_equipments,
            start=self.today_8am + relativedelta(day=1),
            employee=self.employee_tech_johnny,
        )
        self.assertEqual(len(event.of_equipment_ids), 5)
        self.assertRecordValues(
            new_event.of_linked_equipment_ids,
            [
                {
                    "equipment_id": equipment.id,
                    "equipment_report_tmpl_id": self.eq_report_tmpl_maintenance.id,
                    "task_id": self.task_sweeping.id,
                }
                for equipment in (equipments + self.equipment_wood_stove_jh)
            ],
        )

    def test_03_service_request_equipment_removal_nok(self):
        """
        Test the removal of an equipment from a service request with equipments.

        We cannot remove an equipment from a service request if it is linked to a calendar event.

        (Only when updating the service request from the form or directly from `of.service.request.write()`)
        """
        event = self._create_events_from_service_request(self.service_request_w_equipments)

        link_to_remove = self.service_request_w_equipments.linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_id == self.equipment_wood_stove_jc
        )

        with self.assertRaises(UserError) as cannot_remove_error:
            with Form(self.service_request_w_equipments) as service_request_form:
                service_request_form.linked_equipment_ids.remove(
                    index=self.service_request_w_equipments.linked_equipment_ids.ids.index(link_to_remove.id)
                )

        self.assertEqual(
            "Vous ne pouvez pas supprimer un équipement lié à une ou plusieurs interventions.\n"
            "Veuillez supprimer l'équipement pour les interventions concernées.\n\n"
            "Interventions liées :\n"
            f"- {event.name} (id: {event.id})",
            cannot_remove_error.exception.args[0],
        )

    def test_04_service_request_equipment_removal_ok(self):
        """
        Test the removal of an equipment from a service request with equipments.

        The removed equipment should be removed from the existing calendar event to allow the removal of the equipment
        from the service request.

        (Only when updating the service request from the form or directly from `of.service.request.write()`)
        """
        event = self._create_events_from_service_request(self.service_request_w_equipments)

        request_link_to_remove = self.service_request_w_equipments.linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_id == self.equipment_wood_stove_jc
        )
        with Form(event) as event_form:
            event_form.of_linked_equipment_ids.remove(
                index=event.of_linked_equipment_ids.ids.index(
                    event.of_linked_equipment_ids.filtered(lambda lnk: lnk.request_link_id == request_link_to_remove).id
                )
            )
        with Form(self.service_request_w_equipments) as service_request_form:
            service_request_form.linked_equipment_ids.remove(
                index=self.service_request_w_equipments.linked_equipment_ids.ids.index(request_link_to_remove.id)
            )

    def test_05_service_request_equipement_lnk_update(self):
        """
        Test the update of an equipment link from a service request with equipments.

        The update of an equipment link should be propagated to the existing calendar event.
        Equipment intervention lines should be updated accordingly.

        (Only when updating the service request from the form or directly from `of.service.request.write()`)
        """
        event = self._create_events_from_service_request(self.service_request_w_equipments)

        self.assertRecordValues(
            self.service_request_w_equipments.equipment_intervention_ids,
            [
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc.id},
                {"event_id": event.id, "equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_apt.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_ch.id},
            ],
        )

        request_link_to_update = self.service_request_w_equipments.linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_id == self.equipment_wood_stove_jc
        )

        fresh_new_equipment = self.env["of.equipment"].create(
            {
                "name": "JC/FRESH NEW EQUIPMENT",
                "product_id": self.product_wood_stove.id,
                "customer_id": self.customer_johnny_crash.id,
                "site_address_id": self.customer_johnny_crash.id,
            }
        )
        with Form(self.service_request_w_equipments) as service_request_form:
            with service_request_form.linked_equipment_ids.edit(
                index=self.service_request_w_equipments.linked_equipment_ids.ids.index(request_link_to_update.id)
            ) as request_link_form:
                request_link_form.equipment_id = fresh_new_equipment
                request_link_form.equipment_report_tmpl_id = self.eq_report_tmpl_aftersales_service

        event_link_to_update = event.of_linked_equipment_ids.filtered(
            lambda lnk: lnk.request_link_id == request_link_to_update
        )
        self.assertEqual(event_link_to_update.equipment_id, fresh_new_equipment)
        self.assertEqual(event_link_to_update.equipment_report_tmpl_id, self.eq_report_tmpl_aftersales_service)

        # Equipment intervention line for the switched equipment should have been updated accordingly
        self.assertEqual(
            self.service_request_w_equipments.equipment_intervention_ids.filtered(
                lambda eq_event: eq_event.event_link_id == event_link_to_update
            ).equipment_id,
            fresh_new_equipment,
        )

    def test_06_calendar_event_lnk_update(self):
        """
        Test the update of an equipment link from a calendar event with equipments.

        The update of an equipment link should be propagated to the service request.

        (Only when updating the event from the form or directly from `of.calendar.event.write()`)
        """
        event = self._create_events_from_service_request(self.service_request_w_equipments)

        event_link_to_update = event.of_linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_id == self.equipment_wood_stove_jc
        )

        fresh_new_equipment = self.env["of.equipment"].create(
            {
                "name": "JC/FRESH NEW EQUIPMENT",
                "product_id": self.product_wood_stove.id,
                "customer_id": self.customer_johnny_crash.id,
                "site_address_id": self.customer_johnny_crash.id,
            }
        )
        with Form(event) as event_form:
            with event_form.of_linked_equipment_ids.edit(
                index=event.of_linked_equipment_ids.ids.index(event_link_to_update.id)
            ) as event_link_form:
                event_link_form.equipment_id = fresh_new_equipment
                event_link_form.equipment_report_tmpl_id = self.eq_report_tmpl_aftersales_service

        self.assertEqual(event_link_to_update.request_link_id.equipment_id, fresh_new_equipment)
        self.assertEqual(
            event_link_to_update.request_link_id.equipment_report_tmpl_id, self.eq_report_tmpl_aftersales_service
        )

        # Equipment intervention line for the switched equipment should have been updated accordingly
        self.assertEqual(
            self.service_request_w_equipments.equipment_intervention_ids.filtered(
                lambda eq_event: eq_event.event_link_id == event_link_to_update
            ).equipment_id,
            fresh_new_equipment,
        )

    def test_07_calendar_event_equipment_addition(self):
        """
        Test the addition of an equipment to a calendar event with equipments.

        The new added equipment should be added to the service request and the equipment intervention lines should be
        created accordingly.

        (Only when updating the event from the form or directly from `of.calendar.event.write()`)
        """
        event = self._create_events_from_service_request(self.service_request_w_equipments)

        # Check current values of linked equipment before adding a new equipment
        self.assertRecordValues(
            self.service_request_w_equipments.linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
                {"equipment_id": self.equipment_wood_stove_jc_apt.id},
                {"equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"equipment_id": self.equipment_wood_stove_jc_ch.id},
            ],
        )
        # Check current values of equipment intervention lines before adding a new equipment
        self.assertRecordValues(
            self.service_request_w_equipments.equipment_intervention_ids,
            [
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc.id},
                {"event_id": event.id, "equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_apt.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_ch.id},
            ],
        )

        # Add a new equipment to the event
        fresh_new_equipment = self.env["of.equipment"].create(
            {
                "name": "JC/FRESH NEW EQUIPMENT",
                "product_id": self.product_wood_stove.id,
                "customer_id": self.customer_johnny_crash.id,
                "site_address_id": self.customer_johnny_crash.id,
            }
        )
        with Form(event) as event_form:
            with event_form.of_linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = fresh_new_equipment
                equipment_form.equipment_report_tmpl_id = self.eq_report_tmpl_aftersales_service

        # Check that the new equipment has been added to the service request
        self.assertRecordValues(
            self.service_request_w_equipments.linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
                {"equipment_id": self.equipment_wood_stove_jc_apt.id},
                {"equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"equipment_id": self.equipment_wood_stove_jc_ch.id},
                {"equipment_id": fresh_new_equipment.id},
            ],
        )

        # Check that the new equipment has been added to the equipment intervention lines
        self.assertRecordValues(
            self.service_request_w_equipments.equipment_intervention_ids,
            [
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_apt.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_mh.id},
                {"event_id": event.id, "equipment_id": self.equipment_wood_stove_jc_ch.id},
                {"event_id": event.id, "equipment_id": self.equipment_ash_vacuum_cleaner_jc.id},
                {"event_id": event.id, "equipment_id": fresh_new_equipment.id},
            ],
        )

    def test_10_post_message_when_calendar_equipment_link_created(self):
        """
        Test the message post on the event and the service request when a calendar equipment link line is created.
        """

        event = self._create_events_from_service_request(self.service_request_w_equipments)

        fresh_new_equipment = self.env["of.equipment"].create(
            {
                "name": "JC/FRESH NEW EQUIPMENT",
                "product_id": self.product_wood_stove.id,
                "customer_id": self.customer_johnny_crash.id,
                "site_address_id": self.customer_johnny_crash.id,
            }
        )

        with patch("odoo.addons.mail.models.mail_thread.MailThread.message_post") as message_post_mock:
            with Form(event) as event_form:
                with event_form.of_linked_equipment_ids.new() as equipment_form:
                    equipment_form.equipment_id = fresh_new_equipment

            message_post_mock.assert_called()
            message_post_mock.assert_any_call(
                body=f"L'équipement {fresh_new_equipment.name} a été ajouté depuis l'intervention "
                f"{event._get_html_link()}."
            )

    def test_11_post_message_when_calendar_equipment_link_updated(self):
        """
        Test the message post on the event and the service request when a calendar equipment link line is updated.
        """

        event = self._create_events_from_service_request(self.service_request_w_equipments)

        event_link_to_update = event.of_linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_id == self.equipment_wood_stove_jc
        )

        fresh_new_equipment = self.env["of.equipment"].create(
            {
                "name": "JC/FRESH NEW EQUIPMENT",
                "product_id": self.product_wood_stove.id,
                "customer_id": self.customer_johnny_crash.id,
                "site_address_id": self.customer_johnny_crash.id,
            }
        )
        with patch("odoo.addons.mail.models.mail_thread.MailThread.message_post") as message_post_mock:
            with Form(event) as event_form:
                with event_form.of_linked_equipment_ids.edit(
                    index=event.of_linked_equipment_ids.ids.index(event_link_to_update.id)
                ) as event_link_form:
                    event_link_form.equipment_id = fresh_new_equipment

            message_post_mock.assert_called()

            changes = event_link_to_update._get_changes_message_post(
                {"equipment_id": self.equipment_wood_stove_jc.id},
                {"equipment_id": fresh_new_equipment.id},
            )
            expected_body = (
                f"Les détails de l'équipement ont été mis à jour pour {self.equipment_wood_stove_jc.name}.<br/>"
                f"{changes}"
            )
            message_post_mock.assert_any_call(body=expected_body)
            expected_body = (
                f"Les détails de l'équipement ont été mis à jour sur l'intervention "
                f"({event._get_html_link()}) pour {self.equipment_wood_stove_jc.name}.<br/>"
                f"{changes}"
            )
            message_post_mock.assert_any_call(body=expected_body)

    def test_12_post_message_when_request_equipment_link_updated(self):
        """
        Test the message post on the event and the service request when an request equipment link line is updated.
        """

        self._create_events_from_service_request(self.service_request_w_equipments)

        request_link_to_update = self.service_request_w_equipments.linked_equipment_ids.filtered(
            lambda lnk: lnk.equipment_id == self.equipment_wood_stove_jc
        )

        fresh_new_equipment = self.env["of.equipment"].create(
            {
                "name": "JC/FRESH NEW EQUIPMENT",
                "product_id": self.product_wood_stove.id,
                "customer_id": self.customer_johnny_crash.id,
                "site_address_id": self.customer_johnny_crash.id,
            }
        )
        with patch("odoo.addons.mail.models.mail_thread.MailThread.message_post") as message_post_mock:
            with Form(self.service_request_w_equipments) as service_request_form:
                with service_request_form.linked_equipment_ids.edit(
                    index=self.service_request_w_equipments.linked_equipment_ids.ids.index(request_link_to_update.id)
                ) as request_link_form:
                    request_link_form.equipment_id = fresh_new_equipment

            message_post_mock.assert_called()

            changes = request_link_to_update._get_changes_message_post(
                {"equipment_id": self.equipment_wood_stove_jc.id},
                {"equipment_id": fresh_new_equipment.id},
            )
            expected_body = (
                f"Les détails de l'équipement ont été mis à jour pour {self.equipment_wood_stove_jc.name}.<br/>"
                f"{changes}"
            )
            message_post_mock.assert_any_call(body=expected_body)
            expected_body = (
                f"Les détails de l'équipement ont été mis à jour sur la demande d'intervention "
                f"({self.service_request_w_equipments._get_html_link()}) pour {self.equipment_wood_stove_jc.name}.<br/>"
                f"{changes}"
            )
            message_post_mock.assert_any_call(body=expected_body)

    def _create_events_from_service_request(self, service_request, start=False, employee=False):
        """Helper method to create events from a service request."""
        if not start:
            start = self.today_8am
        if not employee:
            employee = self.employee_tech_johnny
        action_wizard = service_request.action_button_create_intervention()
        wizard = self.env["of.service.request.create.intervention.wizard"].browse(action_wizard["res_id"])
        wizard.start_date = start
        wizard.employee_id = employee
        action_event = wizard.action_button_create_intervention()
        event_ids = action_event["domain"][0][2]
        return self.env["calendar.event"].browse(event_ids)
