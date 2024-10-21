# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.of_equipment.tests.common import TestOFEquipmentCommon


@freeze_time("2024-11-13")
class TestOFCalendarEventEquipmentLines(TestOFEquipmentCommon):
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

    def test_01_create_event_with_equipment_manual(self):
        """Test the creation of equipment lines when creating an event with equipment manually with O2M fields."""
        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as line_form:
                line_form.equipment_id = self.equipment_wood_stove_jc
                line_form.equipment_report_tmpl_id = self.eq_report_tmpl_maintenance
            with event_form.of_linked_equipment_ids.new() as line_form:
                line_form.equipment_id = self.equipment_ash_vacuum_cleaner_jc
                line_form.equipment_report_tmpl_id = self.eq_report_tmpl_maintenance
                with self.assertRaises(AssertionError) as update_task_error:
                    # User can't change the task_id, for now, its a readonly field in the form view
                    line_form.task_id = self.task_aftersales_service
            self.assertEqual("can't write on readonly field task_id", update_task_error.exception.args[0])

        self.assertRecordValues(
            self.event.of_linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id, "task_id": self.task_sweeping.id},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": self.task_sweeping.id},
            ],
        )

    def test_02_create_event_with_equipment_wizard(self):
        """Test the creation of equipment lines when creating an event with equipment using the wizard."""
        self._event_wizard_add_equipment([self.equipment_wood_stove_jc.id, self.equipment_ash_vacuum_cleaner_jc.id])

        self.assertRecordValues(
            self.event.of_linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id, "task_id": self.task_sweeping.id},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": self.task_sweeping.id},
            ],
        )

    def test_03_create_service_request_one_equipment(self):
        """Test the creation of a service request with only one equipment.
        The `linked_equipment_ids` field should be filled automatically with the equipment linked to the customer
        as there is only one equipment available for the customer."""
        event = self.env["calendar.event"].create(
            {
                "name": "Test Event 1",
                "of_type": "intervention",
                "start": fields.Datetime.now().replace(hour=14, minute=30, second=0),
                "stop": fields.Datetime.now().replace(hour=15, minute=30, second=0),
                "of_company_id": self.company_fr.id,
                "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                "of_partner_id": self.customer_johnny_holiday.id,
                "of_use_equipment": True,
                "of_template_id": self.template_maintenance_equipment.id,
            }
        )
        self.assertEqual(len(event.of_linked_equipment_ids), 1)
        self.assertRecordValues(event.of_linked_equipment_ids, [{"equipment_id": self.equipment_wood_stove_jh.id}])

    def test_04_event_switch_report_template_link(self):
        """
        Test the functionality of switching the report template link for an event's equipment.

        The test ensures that the equipment report template can be switched correctly and the associated task ID
        is updated accordingly.
        """
        self._event_wizard_add_equipment([self.equipment_wood_stove_jc.id, self.equipment_ash_vacuum_cleaner_jc.id])

        self.assertRecordValues(
            self.event.of_linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id, "task_id": self.task_sweeping.id},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": self.task_sweeping.id},
            ],
        )

        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.edit(0) as line_form:
                line_form.equipment_report_tmpl_id = self.eq_report_tmpl_aftersales_service

        self.assertRecordValues(
            self.event.of_linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id, "task_id": self.task_aftersales_service.id},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": self.task_sweeping.id},
            ],
        )

    def test_05_event_compute_duration(self):
        """Test the computation of the event's duration when adding equipment to the event.

        The test ensures that the event's duration is computed correctly when adding equipment to the event, with or
        without a task.

        Event duration is computed as follows:
            `([Task duration on the Event] * [Number of links without task]) + [Sum of durations of links with task]`
        """
        self._event_wizard_add_equipment([self.equipment_wood_stove_jc.id, self.equipment_ash_vacuum_cleaner_jc.id])

        # All links have a duration of 1.5 hours
        self.assertEqual(self.event.duration, 3.0)

        # Add a link without a task
        self.event.write(
            {
                "of_linked_equipment_ids": [
                    Command.create(
                        {
                            "equipment_id": self.equipment_wood_stove_jc.id,
                        }
                    )
                ]
            }
        )
        self.event.of_linked_equipment_ids[2].write({"equipment_report_tmpl_id": False, "task_id": False})

        # (1.5 * 1) + (1.5 + 1.5) = 4.5
        self.assertEqual(self.event.duration, 4.5)

        # Change task with a duration of 3 hours
        self.event.of_linked_equipment_ids[0].write(
            {"equipment_report_tmpl_id": self.eq_report_tmpl_aftersales_service}
        )

        # (1.5 * 1) + (3.0 + 1.5) = 6.0
        self.assertEqual(self.event.duration, 6.0)

        # Remove one link
        self.event.of_linked_equipment_ids[1].unlink()

        # (1.5 * 1) + 3.0 = 4.5
        self.assertEqual(self.event.duration, 4.5)

        # Remove the last link with a task
        self.event.of_linked_equipment_ids[0].unlink()

        # 1.5 * 1 = 1.5
        self.assertEqual(self.event.duration, 1.5)

    def test_06_compute_equipment_ids(self):
        """
        Test the computation of the event's `equipment_ids` field.

        The test ensures that the event's equipment_ids field is computed correctly when adding/updating/removing
        equipment to the event.
        """
        self._event_wizard_add_equipment([self.equipment_wood_stove_jc.id, self.equipment_ash_vacuum_cleaner_jc.id])

        self.assertEqual(
            self.event.of_equipment_ids, self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc
        )

        with Form(self.event) as event_form:
            with event_form.of_linked_equipment_ids.new() as line_form:
                line_form.equipment_id = self.equipment_ash_vacuum_cleaner_jc

        # M2M field, equipments appears only once
        self.assertEqual(
            self.event.of_equipment_ids, self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc
        )

        # Remove one link that has the same equipment as another link
        self.event.of_linked_equipment_ids[2].unlink()

        # Equipments are still present in the M2M field
        self.assertEqual(
            self.event.of_equipment_ids, self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc
        )

        # Remove the last link with the same equipment
        self.event.of_linked_equipment_ids[1].unlink()

        # Equipment is removed from the M2M field
        self.assertEqual(self.event.of_equipment_ids, self.equipment_wood_stove_jc)

    def test_07_event_delete_equipment_links(self):
        """Test the deletion of equipment links for an event with button."""
        self._event_wizard_add_equipment([self.equipment_wood_stove_jc.id, self.equipment_ash_vacuum_cleaner_jc.id])

        self.assertEqual(
            self.event.of_equipment_ids, self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc
        )

        self.event.action_button_remove_all_equipments()

        self.assertFalse(self.event.of_linked_equipment_ids)
        self.assertFalse(self.event.of_equipment_ids)

    def test_08_event_state_done_cannot_update_equipment_link(self):
        """Test that equipment links cannot be updated for done or cancelled events."""

        def _assert_cannot_update_equipment_link():
            with self.assertRaises(AssertionError) as not_editable_error_done:
                with Form(self.event) as event_form:
                    with event_form.of_linked_equipment_ids.edit(0) as line_form:
                        line_form.equipment_report_tmpl_id = self.eq_report_tmpl_aftersales_service
            self.assertEqual("field of_linked_equipment_ids is not editable", not_editable_error_done.exception.args[0])

            with self.assertRaises(UserError) as not_editable_error_done:
                self.event.of_linked_equipment_ids[0].write(
                    {"equipment_report_tmpl_id": self.eq_report_tmpl_aftersales_service}
                )
            self.assertEqual(
                "Vous ne pouvez pas changer l'équipement des interventions terminées ou annulées.",
                not_editable_error_done.exception.args[0],
            )

        # Create an event with equipment
        self._event_wizard_add_equipment([self.equipment_wood_stove_jc.id, self.equipment_ash_vacuum_cleaner_jc.id])

        # Set the event to done
        self.event.action_button_done()

        # Check that we cannot update the equipment link
        _assert_cannot_update_equipment_link()

        # Set the event back to draft
        self.event.action_button_draft()

        # We can update the equipment link
        self.event.of_linked_equipment_ids[0].write(
            {"equipment_report_tmpl_id": self.eq_report_tmpl_aftersales_service}
        )

        # Set the event to cancelled
        self.event.action_button_cancel()

        # Check that we cannot update the equipment link
        _assert_cannot_update_equipment_link()

    def test_09_event_state_done_cannot_delete_equipment_link(self):
        """Test that equipment links cannot be deleted for done or cancelled events."""

        def _assert_cannot_delete_equipment_link():
            with self.assertRaises(AssertionError) as delete_error_done:
                with Form(self.event) as event_form:
                    event_form.of_linked_equipment_ids.remove(0)
            self.assertEqual("field of_linked_equipment_ids is not editable", delete_error_done.exception.args[0])

            with self.assertRaises(UserError) as delete_error_done:
                self.event.of_linked_equipment_ids[0].unlink()
            self.assertEqual(
                "Vous ne pouvez pas supprimer d'équipement pour des interventions terminées ou annulées.",
                delete_error_done.exception.args[0],
            )

        # Create an event with equipment
        self._event_wizard_add_equipment([self.equipment_wood_stove_jc.id, self.equipment_ash_vacuum_cleaner_jc.id])

        # Set the event to done
        self.event.action_button_done()

        # Check that we cannot delete the equipment link
        _assert_cannot_delete_equipment_link()

        # Set the event back to draft
        self.event.action_button_draft()

        # We can delete the equipment link
        self.event.of_linked_equipment_ids[0].unlink()

        # Set the event to cancelled
        self.event.action_button_cancel()

        # Check that we cannot delete the equipment link
        _assert_cannot_delete_equipment_link()

    def _event_wizard_add_equipment(self, equipment_ids):
        """Helper method to create a wizard to add equipment to an event."""
        wizard = (
            self.env["of.equipment.link.create.wizard"]
            .with_context(default_event_id=self.event.id)
            .create({"equipment_ids": [Command.set(equipment_ids)]})
        )
        wizard.action_button_select_equipments()
        return wizard
