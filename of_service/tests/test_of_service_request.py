# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields

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

    def test_02_compute_fiscal_position_id(self):
        """Test that the fiscal position is computed correctly when the service request is created.
        Also test that the fiscal position is recomputed when the task is changed and when the fiscal position
        is removed.
        """
        self.assertEqual(self.service_request.fiscal_position_id, self.service_request.task_id.fiscal_position_id)

        self.service_request.fiscal_position_id = False
        self.service_request._compute_fiscal_position_id()

        # The fiscal position should be recomputed when the task is changed and when the fiscal position is removed
        self.assertEqual(self.service_request.fiscal_position_id, self.service_request.task_id.fiscal_position_id)

        # Remove the fiscal position from the request to ensure that the fiscal position is recomputed
        self.service_request.fiscal_position_id = False
        self.service_request.task_id = self.task_installation

        self.assertEqual(self.service_request.fiscal_position_id, self.service_request.task_id.fiscal_position_id)

    def test_03_compute_line_ids(self):
        """Test that the line_ids are computed correctly when the service request is created."""

        # Task has no product, so no line should be created
        self.service_request._compute_line_ids()
        self.assertEqual(len(self.service_request.line_ids), 0)

        # switch to a task with a product
        self.service_request.task_id = self.task_installation

        self.assertEqual(len(self.service_request.line_ids), 1)
        self.assertEqual(self.service_request.line_ids[0].product_id, self.service_request.task_id.product_id)
        self.assertEqual(self.service_request.line_ids[0].qty, 1)
        self.assertEqual(self.service_request.line_ids[0].price_unit, self.service_request.task_id.product_id.lst_price)
        self.assertEqual(self.service_request.line_ids[0].name, self.service_request.task_id.product_id.name)

    def test_04_compute_template_related_fields(self):
        """Test that the fields related to the template are computed correctly."""
        self.template_installation.fiscal_position_id = self.fiscal_pos_20

        self.service_request.template_id = self.template_installation

        self.assertEqual(self.service_request.task_id, self.template_installation.task_id)
        self.assertEqual(self.service_request.type_id, self.template_installation.type_id)
        self.assertEqual(
            self.service_request.fiscal_position_id,
            self.template_installation.fiscal_position_id or self.service_request.fiscal_position_id,
        )

        # there should be 2 lines, one for the task and one for the template
        self.assertEqual(len(self.service_request.line_ids), 2)
        self.assertEqual(self.service_request.line_ids[0].product_id, self.task_installation.product_id)
        self.assertEqual(self.service_request.line_ids[0].qty, 1)
        self.assertEqual(self.service_request.line_ids[0].price_unit, self.task_installation.product_id.lst_price)
        self.assertEqual(self.service_request.line_ids[0].name, 'Poêle à bois')

        self.assertEqual(self.service_request.line_ids[1].product_id, self.product_ash_vacuum_cleaner)
        self.assertEqual(self.service_request.line_ids[1].qty, 1)
        self.assertEqual(self.service_request.line_ids[1].price_unit, 125.0)
        self.assertEqual(
            self.service_request.line_ids[1].name, 'Aspirateur à cendres\nAspirateur à cendres pour poêle à bois'
        )
