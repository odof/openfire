# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import Form

from odoo.addons.of_service.tests.common import TestOFServiceCommon


class TestOFServiceRequest(TestOFServiceCommon):
    @freeze_time('2024-02-09 09:00:00')
    def setUp(self):
        super().setUp()

        self.service_request = self.env['of.service.request'].create(
            {
                'partner_id': self.partner_tony.id,
                'address_id': self.partner_tony.id,
                'task_id': self.task_sweeping.id,
                'type_id': self.env.ref('of_service.of_service_request_type_technical').id,
                'company_id': self.company_fr.id,
                'next_date': fields.Date.today(),
                'end_date': fields.Date.today() + relativedelta(days=15),
            }
        )

    def test_01_compute_name(self):
        self.assertEqual(self.service_request.name, "Ramonage Tony Tagada 35000")
        self.partner_tony.zip = '75000'
        self.service_request._compute_name()
        self.assertEqual(self.service_request.name, "Ramonage Tony Tagada 75000")

        self.service_request.task_id = self.task_installation
        self.service_request._compute_name()
        self.assertEqual(self.service_request.name, "Installation poêle à bois Tony Tagada 75000")

    def test_02_compute_template_related_fields(self):
        """Test that the fields related to the template are computed correctly."""
        self.template_installation.fiscal_position_id = self.fiscal_pos_20

        self.service_request.template_id = self.template_installation

        self.assertEqual(self.service_request.task_id, self.template_installation.task_id)
        self.assertEqual(self.service_request.type_id, self.template_installation.type_id)
        self.assertEqual(
            self.service_request.fiscal_position_id,
            self.template_installation.fiscal_position_id or self.service_request.fiscal_position_id,
        )

        # there should be 1 line added from the template
        self.assertEqual(len(self.service_request.line_ids), 1)
        self.assertEqual(self.service_request.line_ids[0].product_id, self.product_ash_vacuum_cleaner)
        self.assertEqual(self.service_request.line_ids[0].qty, 1)
        self.assertEqual(self.service_request.line_ids[0].price_unit, 125.0)
        self.assertEqual(
            self.service_request.line_ids[0].name, 'Aspirateur à cendres\nAspirateur à cendres pour poêle à bois'
        )

    def test_03_compute_states(self):
        """
        Test that the state is computed correctly for a service request.

        This test method verifies the different states of a service request based on various scenarios.
        It checks if the state is correctly updated when changing the task, setting dates, creating interventions,
        and confirming/done actions on interventions.

        The different states tested are:
        - 'draft': Initial state of the service request.
        - 'late': Service request is considered late due to the freeze_time in setUp.
        - 'nothing_to_plan': No dates are set, so the state should be 'nothing_to_plan'.
        - 'to_plan': Set next_date and end_date to a far date, so the state should be 'to_plan'.
        - 'to_plan_quickly': Set next_date and end_date to a near date, so the state should be 'to_plan_quickly'.
        - 'part_planned': Service request is not fully planned yet.
        - 'all_planned': All interventions are planned and the duration of the service request matches the sum of
            interventions' duration.
        - 'done': All interventions are done.
        """

        # Change task of service request to a task with a greater duration
        self.service_request.task_id = self.task_installation

        self.assertEqual(self.service_request.state, 'draft')
        self.service_request.action_button_validate()
        self.assertEqual(self.service_request.state, 'late')  # we are late because of the freeze_time in setUp

        with Form(self.service_request) as request_form:
            # No dates are set, so the state should be 'nothing_to_plan'
            request_form.next_date = False
            request_form.end_date = False
            self.assertEqual(request_form.state, 'nothing_to_plan')

            # Set next_date and end_date to a far date, so the state should be 'to_plan'
            request_form.next_date = fields.Date.today() + relativedelta(days=35)
            request_form.end_date = fields.Date.today() + relativedelta(days=50)
            self.assertEqual(request_form.state, 'to_plan')

            # Set next_date and end_date to a near date, so the state should be 'to_plan_quickly'
            request_form.next_date = fields.Date.today() + relativedelta(days=10)
            request_form.end_date = fields.Date.today() + relativedelta(days=20)
            self.assertEqual(request_form.state, 'to_plan_quickly')
            self.service_request = request_form.save()

        # Create an intervention from the service request
        wizard = self.env['of.service.request.create.intervention.wizard'].create(
            {
                'employee_id': self.employee_tech_bruce.id,
                'start_date': self.service_request.next_date + relativedelta(hours=9, minutes=0),
                'line_ids': [
                    Command.create(
                        {
                            'request_id': self.service_request.id,
                        }
                    )
                ],
            }
        )
        returned_action = wizard.action_button_create_intervention()
        event_ids = returned_action['domain'][0][2]
        first_intervention = self.env['calendar.event'].browse(event_ids)

        # Change duration of intervention to split the task in many interventions
        first_intervention.duration = 4

        # Service request is not fully planned yet because only 4 hours of the 8 hours task are planned
        self.assertEqual(self.service_request.state, 'part_planned')

        # Create a second intervention from the service request to test the state
        wizard = self.env['of.service.request.create.intervention.wizard'].create(
            {
                'employee_id': self.employee_tech_bruce.id,
                'start_date': self.service_request.next_date + relativedelta(hours=13, minutes=30),
                'line_ids': [
                    Command.create(
                        {
                            'request_id': self.service_request.id,
                        }
                    )
                ],
            }
        )
        returned_action = wizard.action_button_create_intervention()
        event_ids = returned_action['domain'][0][2]
        second_intervention = self.env['calendar.event'].browse(event_ids)
        second_intervention.duration = 4

        # The state should be 'all_planned' now because duration of service request is equal to the sum of the
        # interventions' duration created from the service request
        self.assertEqual(self.service_request.state, 'all_planned')

        # The state should be 'all_planned' because not all interventions are done
        first_intervention.action_button_confirm()
        first_intervention.action_button_done()
        self.assertEqual(self.service_request.state, 'all_planned')

        # The state should be 'done' because all interventions are done
        second_intervention.action_button_confirm()
        second_intervention.action_button_done()
        self.assertEqual(self.service_request.state, 'done')
