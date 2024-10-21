# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.of_equipment_service.tests.common import TestOFEquipmentServiceCommon


@freeze_time("2024-11-14")
class TestOFServiceRequest(TestOFEquipmentServiceCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.service_request_link_obj = cls.env["of.service.request.equipment.link"]
        cls.today_8am = fields.Datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)

        # Create a service request without equipment
        cls.service_request = cls.env["of.service.request"].create(
            {
                "partner_id": cls.customer_johnny_crash.id,
                "address_id": cls.customer_johnny_crash.id,
                "template_id": cls.template_maintenance_equipment.id,
                "task_id": cls.task_installation.id,
                "duration": 1,
                "type_id": cls.env.ref("of_service.of_service_request_type_installation").id,
                "company_id": cls.company_fr.id,
                "use_equipment": True,
                "employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                "next_date": cls.today_8am.date(),
                "end_date": cls.today_8am.date() + relativedelta(days=15),
            }
        )

    def test_01_create_service_request_use_equipment_nok(self):
        """Test the creation of a service request without equipment.
        That should raise an error as the use_equipment field is not True (`linked_equipment_ids` is not visible)."""
        self.service_request.use_equipment = False
        with Form(self.service_request) as request_form:
            with self.assertRaises(AssertionError) as create_service_request_error:  # use_equipment is False
                with request_form.linked_equipment_ids.new() as equipment_form:
                    equipment_form.equipment_id = self.equipment_wood_stove
        self.assertEqual("field linked_equipment_ids is not visible", create_service_request_error.exception.args[0])

    def test_02_service_request_with_one_equipment(self):
        """Test the creation of a service request with only one equipment.
        The `linked_equipment_ids` field should be filled automatically with the equipment linked to the customer
        as there is only one equipment available for the customer."""
        self.service_request.partner_id = self.customer_johnny_holiday
        self.service_request.address_id = self.customer_johnny_holiday
        self.service_request.use_equipment = True
        self.assertEqual(len(self.service_request.linked_equipment_ids), 1)
        self.assertRecordValues(
            self.service_request.linked_equipment_ids, [{"equipment_id": self.equipment_wood_stove_jh.id}]
        )

    def test_03_service_request_available_equipments(self):
        """
        Test the availability of equipment linked to calendar events based on the service request customer/address.
        """
        customer_one_equipment = self.env["res.partner"].create({"name": "New Customer (with one equipment)"})
        customer_no_equipment = self.env["res.partner"].create({"name": "New Customer (with one equipment)"})
        new_equipment = self.env["of.equipment"].create(
            {
                "name": "New Equipment",
                "customer_id": customer_one_equipment.id,
                "site_address_id": customer_one_equipment.id,
                "product_id": self.product_wood_stove.id,
            }
        )

        # We should be able to select all equipments linked to service request customer, here Johnny Crash
        self.assertEqual(
            self.service_request_link_obj.new({"service_request_id": self.service_request.id}).equipment_ids_domain.ids,
            (
                self.equipment_wood_stove_jc
                + self.equipment_wood_stove_jc_apt
                + self.equipment_wood_stove_jc_mh
                + self.equipment_wood_stove_jc_ch
                + self.equipment_ash_vacuum_cleaner_jc
            ).ids,
        )

        # Change the customer to a customer with only one equipment
        self.service_request.partner_id = customer_one_equipment
        self.service_request.address_id = customer_one_equipment
        self.assertEqual(self.service_request.partner_id, customer_one_equipment)
        self.assertEqual(self.service_request.address_id, customer_one_equipment)

        # We should be able to select the only equipment linked to the new customer
        self.assertEqual(
            self.service_request_link_obj.new({"service_request_id": self.service_request.id}).equipment_ids_domain.ids,
            new_equipment.ids,
        )

        # Set service request address to Johnny Crash's address
        self.service_request.address_id = self.customer_johnny_crash.id
        self.assertEqual(self.service_request.partner_id, customer_one_equipment)
        self.assertEqual(self.service_request.address_id, self.customer_johnny_crash)

        # We should be able to select all equipments of Johnny Crash and the new equipment
        self.assertEqual(
            self.service_request_link_obj.new({"service_request_id": self.service_request.id}).equipment_ids_domain.ids,
            (
                self.equipment_wood_stove_jc
                + self.equipment_wood_stove_jc_apt
                + self.equipment_wood_stove_jc_mh
                + self.equipment_wood_stove_jc_ch
                + self.equipment_ash_vacuum_cleaner_jc
                + new_equipment
            ).ids,
        )

        # Then finally, set the customer to a customer with no equipment
        self.service_request.partner_id = customer_no_equipment
        self.service_request.address_id = customer_no_equipment
        self.assertEqual(self.service_request.partner_id, customer_no_equipment)
        self.assertEqual(self.service_request.address_id, customer_no_equipment)

        # We should not be able to select any equipment
        self.assertFalse(
            self.service_request_link_obj.new({"service_request_id": self.service_request.id}).equipment_ids_domain
        )

    def test_04_create_service_request_with_equipment_manual(self):
        """Test the creation of equipment lines when creating a service request with equipment manually with O2M
        fields."""
        with Form(self.service_request) as request_form:
            with request_form.linked_equipment_ids.new() as line_form:
                line_form.equipment_id = self.equipment_wood_stove_jc
        self.assertRecordValues(
            self.service_request.linked_equipment_ids,
            [{"equipment_id": self.equipment_wood_stove_jc.id, "task_id": self.task_sweeping.id}],
        )

        # Add template to the service request to ensure that equipment lines will take the template into account and
        # get the correct task
        service_request2 = self.env["of.service.request"].create(self.service_request.copy_data())
        service_request2.template_id = self.template_maintenance_equipment

        with Form(service_request2) as request_form:
            with request_form.linked_equipment_ids.new() as line_form:
                line_form.equipment_id = self.equipment_ash_vacuum_cleaner_jc
        self.assertRecordValues(
            service_request2.linked_equipment_ids,
            [
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": self.task_sweeping.id},
            ],
        )

    def test_05_create_service_request_with_equipment_wizard(self):
        """Test the creation of equipment lines when creating a service request with equipment using the wizard."""
        # Empty template, no task
        self.service_request.template_id = False

        self._service_request_wizard_add_equipment(
            equipments=self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        )

        self.assertRecordValues(
            self.service_request.linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id, "task_id": False},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": False},
            ],
        )

        # Add template to the service request to ensure that equipment lines will take the template into account and
        # get the correct task
        self.service_request.template_id = self.template_maintenance_equipment

        self._service_request_wizard_add_equipment(
            equipments=self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        )

        self.assertRecordValues(
            self.service_request.linked_equipment_ids,
            [
                {"equipment_id": self.equipment_wood_stove_jc.id, "task_id": False},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": False},
                {"equipment_id": self.equipment_wood_stove_jc.id, "task_id": self.task_sweeping.id},
                {"equipment_id": self.equipment_ash_vacuum_cleaner_jc.id, "task_id": self.task_sweeping.id},
            ],
        )

    def test_06_service_request_compute_duration(self):
        """Test the computation of the service request's duration when adding equipment.

        The test ensures that the duration is computed correctly when adding equipment to the service request, with or
        without a task.

        Service request duration is computed as follows:
            `([Task duration on the Request] * [Number of links without task]) + [Sum of durations of links with task]`
        """
        self._service_request_wizard_add_equipment(
            equipments=self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        )

        # All links have a duration of 1.5 hours
        self.assertEqual(self.service_request.duration, 3.0)

        # Add a link without a task
        self.service_request.write(
            {
                "linked_equipment_ids": [
                    Command.create(
                        {
                            "equipment_id": self.equipment_wood_stove_jc.id,
                        }
                    )
                ]
            }
        )
        self.service_request.linked_equipment_ids[2].write({"equipment_report_tmpl_id": False, "task_id": False})

        # (8.0 * 1) + (1.5 + 1.5) = 11.0
        self.assertEqual(self.service_request.duration, 11.0)

        # Change task with a duration of 3 hours
        self.service_request.linked_equipment_ids[0].write(
            {"equipment_report_tmpl_id": self.eq_report_tmpl_aftersales_service}
        )

        # (8.0 * 1) + (3.0 + 1.5) = 12.5
        self.assertEqual(self.service_request.duration, 12.5)

        # Remove one link
        self.service_request.linked_equipment_ids[1].unlink()

        # (8.0 * 1) + 3.0 = 11.0
        self.assertEqual(self.service_request.duration, 11.0)

        # Remove the last link with a task
        self.service_request.linked_equipment_ids[0].unlink()

        # 8.0 * 1 = 8.0
        self.assertEqual(self.service_request.duration, 8.0)

    def test_07_compute_equipment_ids(self):
        """
        Test the computation of the service request's `equipment_ids` field.

        The test ensures that the service request's equipment_ids field is computed correctly when
        adding/updating/removing equipment.
        """
        self._service_request_wizard_add_equipment(
            equipments=self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        )

        self.assertEqual(
            self.service_request.equipment_ids,
            self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc,
        )

        with Form(self.service_request) as request_form:
            with request_form.linked_equipment_ids.new() as line_form:
                line_form.equipment_id = self.equipment_ash_vacuum_cleaner_jc

        # M2M field, equipments appears only once
        self.assertEqual(
            self.service_request.equipment_ids,
            self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc,
        )

        # Remove one link that has the same equipment as another link
        self.service_request.linked_equipment_ids[2].unlink()

        # Equipments are still present in the M2M field
        self.assertEqual(
            self.service_request.equipment_ids,
            self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc,
        )

        # Remove the last link with the same equipment
        self.service_request.linked_equipment_ids[1].unlink()

        # Equipment is removed from the M2M field
        self.assertEqual(self.service_request.equipment_ids, self.equipment_wood_stove_jc)

    def test_08_event_delete_equipment_links(self):
        """Test the deletion of equipment links for an event with button."""
        self._service_request_wizard_add_equipment(
            equipments=self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        )

        self.assertEqual(
            self.service_request.equipment_ids,
            self.equipment_wood_stove_jc | self.equipment_ash_vacuum_cleaner_jc,
        )

        self.service_request.action_button_remove_all_equipments()

        self.assertFalse(self.service_request.linked_equipment_ids)
        self.assertFalse(self.service_request.equipment_ids)

    def test_09_event_state_done_cannot_update_equipment_link(self):
        """Test that equipment links cannot be updated for done or cancelled events."""

        def _assert_cannot_update_equipment_link():
            with self.assertRaises(AssertionError) as not_editable_error_done:
                with Form(self.service_request) as request_form:
                    with request_form.linked_equipment_ids.edit(0) as line_form:
                        line_form.equipment_report_tmpl_id = self.eq_report_tmpl_aftersales_service
            self.assertEqual("field linked_equipment_ids is not editable", not_editable_error_done.exception.args[0])

            with self.assertRaises(UserError) as not_editable_error_done:
                self.service_request.linked_equipment_ids[0].write(
                    {"equipment_report_tmpl_id": self.eq_report_tmpl_aftersales_service}
                )
            self.assertEqual(
                "Vous ne pouvez pas changer l'équipement des demandes d'intervention terminées ou annulées.",
                not_editable_error_done.exception.args[0],
            )

        # Create an event with equipment
        self._service_request_wizard_add_equipment(
            equipments=self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        )

        # Set the event to done
        self.service_request.state = "done"

        # Check that we cannot update the equipment link
        _assert_cannot_update_equipment_link()

        # Set the event back to draft
        self.service_request.action_button_draft()

        # We can update the equipment link
        self.service_request.linked_equipment_ids[0].write(
            {"equipment_report_tmpl_id": self.eq_report_tmpl_aftersales_service}
        )

        # Set the event to cancelled
        self.service_request.action_button_cancel()

        # Check that we cannot update the equipment link
        _assert_cannot_update_equipment_link()

    def test_10_event_state_done_cannot_delete_equipment_link(self):
        """Test that equipment links cannot be deleted for done or cancelled events."""

        def _assert_cannot_delete_equipment_link():
            with self.assertRaises(AssertionError) as delete_error_done:
                with Form(self.service_request) as request_form:
                    request_form.linked_equipment_ids.remove(0)
            self.assertEqual("field linked_equipment_ids is not editable", delete_error_done.exception.args[0])

            with self.assertRaises(UserError) as delete_error_done:
                self.service_request.linked_equipment_ids[0].unlink()
            self.assertEqual(
                "Vous ne pouvez pas supprimer les équipements des demandes d'intervention terminées ou annulées.",
                delete_error_done.exception.args[0],
            )

        # Create an event with equipment
        self._service_request_wizard_add_equipment(
            equipments=self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        )

        # Set the event to done
        self.service_request.state = "done"

        # Check that we cannot delete the equipment link
        _assert_cannot_delete_equipment_link()

        # Set the event back to draft
        self.service_request.action_button_draft()
        self.service_request.type_id = self.env.ref("of_service.of_service_request_type_installation").id

        # We can delete the equipment link
        self.service_request.linked_equipment_ids[0].unlink()

        # Set the event to cancelled
        self.service_request.action_button_cancel()

        # Check that we cannot delete the equipment link
        _assert_cannot_delete_equipment_link()

    def _service_request_wizard_add_equipment(self, service_request=False, equipments=None):
        """Helper method to create a wizard to add equipment to a service request."""
        if equipments is None:
            equipments = self.equipment_wood_stove_jc + self.equipment_ash_vacuum_cleaner_jc
        if not service_request:
            service_request = self.service_request
        wizard = (
            self.env["of.equipment.link.create.wizard"]
            .with_context(default_service_request_id=service_request.id)
            .create({"equipment_ids": [Command.set(equipments.ids)]})
        )
        wizard.action_button_select_equipments()
        return wizard
