# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests.common import Form

from odoo.addons.of_equipment.tests.common import TestOFEquipmentCommon


@freeze_time("2024-11-21")
class TestCalendarEventEquipmentLinkLine(TestOFEquipmentCommon):
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
                "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                "of_partner_id": self.customer_johnny_crash.id,
                "of_use_equipment": True,
                "of_template_id": self.template_maintenance_equipment.id,
                "of_task_id": self.task_sweeping.id,
            }
        )

    def test_01_calendar_event_equipment_link_line_create(self):
        """Test the creation of an equipment link line."""
        self.assertFalse(self.event.of_line_ids, "The event should not have any invoice line yet.")

        # Add a linked equipment with a report template that has a single invoice line.
        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = self.equipment_wood_stove

        # Check the linked equipment.
        self.assertEqual(len(self.event.of_linked_equipment_ids), 1)
        self.assertEqual(self.event.of_linked_equipment_ids[0].equipment_id, self.equipment_wood_stove)
        self.assertEqual(
            self.event.of_linked_equipment_ids[0].equipment_report_tmpl_id,
            self.event.of_template_id.default_equipment_report_tmpl_id,
        )

        # Check the invoice line on the linked equipment.
        self.assertTrue(self.event.of_linked_equipment_ids[0].line_ids)
        self.assertRecordValues(
            self.event.of_linked_equipment_ids[0].line_ids,
            [{"product_id": self.product_consu_a.id, "qty": 1, "price_unit": 150}],
        )

        # Check the invoice line on the event.
        self.assertTrue(self.event.of_line_ids, "The event should have an invoice line.")
        self.assertRecordValues(
            self.event.of_line_ids,
            [{"product_id": self.product_consu_a.id, "qty": 1, "price_unit": 150}],
        )

    def test_02_calendar_event_equipment_link_line_addition(self):
        """Test the creation of an equipment link line."""
        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = self.equipment_wood_stove

        # Add a new invoice line to the linked equipment.
        with Form(self.event.of_linked_equipment_ids[0]) as equipment_form:
            with equipment_form.line_ids.new() as line_form:
                line_form.product_id = self.product_consu_b
                line_form.qty = 2
                line_form.price_unit = 200

        # Check invoice lines the event
        self.assertEqual(len(self.event.of_line_ids), 2)
        self.assertRecordValues(
            self.event.of_line_ids,
            [
                {"product_id": self.product_consu_a.id, "qty": 1, "price_unit": 150},
                {"product_id": self.product_consu_b.id, "qty": 2, "price_unit": 200},
            ],
        )

    def test_03_calendar_event_equipment_link_line_update(self):
        """
        Test the update of an equipment link line and its invoice line on the event.

        The invoice line on the event should be updated when the invoice line on the linked equipment is updated.
        And vice versa.
        """
        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = self.equipment_wood_stove

        self.assertEqual(len(self.event.of_line_ids), 1)
        self.assertRecordValues(
            self.event.of_line_ids,
            [{"product_id": self.product_consu_a.id, "qty": 1, "price_unit": 150}],
        )

        # Update the linked equipment invoicing line.
        with Form(self.event.of_linked_equipment_ids[0].line_ids[0]) as line_form:
            line_form.qty = 2
            line_form.price_unit = 200

        # Check the invoice line on the event.
        self.assertEqual(len(self.event.of_line_ids), 1)
        self.assertRecordValues(
            self.event.of_line_ids,
            [{"product_id": self.product_consu_a.id, "qty": 2, "price_unit": 200}],
        )

        # Update the invoice line on the event.
        with Form(self.event.of_line_ids[0]) as line_form:
            line_form.product_id = self.product_consu_b
            line_form.qty = 3
            line_form.price_unit = 250

        # Check the invoice line on the linked equipment.
        self.assertEqual(len(self.event.of_linked_equipment_ids[0].line_ids), 1)
        self.assertRecordValues(
            self.event.of_linked_equipment_ids[0].line_ids,
            [{"product_id": self.product_consu_b.id, "qty": 3, "price_unit": 250}],
        )

    def test_04_calendar_event_equipment_link_line_delete(self):
        """
        Test the deletion of an equipment link line and its invoice line on the event.

        The invoice line on the event should be deleted when the invoice line on the linked equipment is deleted.
        And vice versa.
        """
        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = self.equipment_wood_stove

        self.assertEqual(len(self.event.of_line_ids), 1)
        self.assertRecordValues(
            self.event.of_line_ids,
            [{"product_id": self.product_consu_a.id, "qty": 1, "price_unit": 150}],
        )

        # Delete the linked equipment invoicing line.
        self.event.of_linked_equipment_ids[0].line_ids.unlink()

        # Check the invoice line on the event.
        self.assertFalse(self.event.of_line_ids, "The event should not have any invoice line.")

        # Add a new invoice line to the linked equipment.
        with Form(self.event.of_linked_equipment_ids[0]) as equipment_form:
            with equipment_form.line_ids.new() as line_form:
                line_form.product_id = self.product_consu_a
                line_form.qty = 1
                line_form.price_unit = 150

        # Check the invoice line on the event.
        self.assertEqual(len(self.event.of_line_ids), 1)
        self.assertRecordValues(
            self.event.of_line_ids,
            [{"product_id": self.product_consu_a.id, "qty": 1, "price_unit": 150}],
        )

        # Delete the invoice line on the event.
        self.event.of_line_ids.unlink()

        # Check the invoice line on the linked equipment.
        self.assertFalse(
            self.event.of_linked_equipment_ids[0].line_ids, "The linked equipment should not have any invoice line."
        )

    def test_05_calendar_event_equipment_link_line_message_post_add(self):
        """
        Test the message post on the event when an equipment link line is created.
        """
        with patch("odoo.addons.mail.models.mail_thread.MailThread.message_post") as message_post_mock:
            with Form(self.event) as event_form:
                with event_form.of_linked_equipment_ids.new() as equipment_form:
                    equipment_form.equipment_id = self.equipment_wood_stove

            message_post_mock.assert_called_once()

            expected_body = (
                "Une nouvelle ligne de facturation a été créée à partir de "
                f"l'équipement {self.equipment_wood_stove.name} : "
                f"{self.eq_report_tmpl_maintenance.line_ids[0].product_id.name_get()[0][1]}"
            )
            message_post_mock.assert_called_with(body=expected_body)

    def test_06_calendar_event_equipment_link_line_message_post_update(self):
        """
        Test the message post on the event when an equipment link line is updated.
        """
        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = self.equipment_wood_stove

        with patch("odoo.addons.mail.models.mail_thread.MailThread.message_post") as message_post_mock:
            with Form(self.event.of_linked_equipment_ids[0].line_ids[0]) as line_form:
                line_form.qty = 2
                line_form.price_unit = 200

            message_post_mock.assert_called_once()

            expected_body = (
                f"Une ligne de facturation a été mise à jour de l'équipement {self.equipment_wood_stove.name} : "
                f"{self.eq_report_tmpl_maintenance.line_ids[0].product_id.name_get()[0][1]}"
            )
            message_post_mock.assert_called_with(body=expected_body)

    def test_07_calendar_event_equipment_link_line_message_post_delete(self):
        """
        Test the message post on the event when an equipment link line is deleted.
        """
        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as equipment_form:
                equipment_form.equipment_id = self.equipment_wood_stove

        with patch("odoo.addons.mail.models.mail_thread.MailThread.message_post") as message_post_mock:
            self.event.of_linked_equipment_ids[0].line_ids.unlink()

            message_post_mock.assert_called_once()

            expected_body = (
                f"Une ligne de facturation a été supprimée de l'équipement {self.equipment_wood_stove.name} : "
                f"{self.eq_report_tmpl_maintenance.line_ids[0].product_id.name_get()[0][1]}"
            )
            message_post_mock.assert_called_with(body=expected_body)
