# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields

from odoo.addons.of_service.tests.common import TestOFServiceCommon


@freeze_time("2025-01-15 07:00:00")
class TestOFSaleOrderLayingDate(TestOFServiceCommon):
    def setUp(self):
        super(TestOFSaleOrderLayingDate, self).setUp()

        self.now_dt = fields.Datetime.now()
        self.request_type_installation = self.env.ref("of_service.of_service_request_type_installation")
        self.request_type_maintenance = self.env.ref("of_service.of_service_request_type_maintenance")
        self.sale_template = self.env["sale.order.template"].create(
            {
                "name": "Test template",
                "of_order_type_id": self.env.ref("sale_order_type.normal_sale_type").id,
                "of_service_mgmt": "sale",
                "of_intervention_template_id": self.template_installation.id,
                "of_fiscal_position_id": self.fiscal_pos_20,
                "sale_order_template_line_ids": [
                    Command.create({"product_id": self.product_consu_a.id, "product_uom_qty": 1}),
                ],
            }
        )

    def test_01_compute_reference_laying_date(self):
        """Test the computation of reference laying date on sale orders."""
        # Create sale order
        order_values = self._prepare_empty_sale_order_values()
        order_values["sale_order_template_id"] = self.sale_template.id
        order = self.env["sale.order"].create(order_values)
        order.action_confirm()

        # We should have one SR here
        self.assertEqual(len(order.of_request_ids), 1)
        service_request = order.of_request_ids[0]

        # Initially no interventions - laying date should be False
        self.assertFalse(order.of_reference_laying_date)
        self.assertEqual(order.of_laying_week, "Non programmée")

        # Create draft intervention - laying date should be set to False as it is not an installation type
        self.env["calendar.event"].create(
            {
                "name": "Test Event",
                "of_type": "intervention",
                "of_company_id": self.company_fr.id,
                "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                "of_partner_id": self.customer_a.id,
                "of_request_id": service_request.id,
                "of_type_id": self.request_type_maintenance.id,
                "start": self.now_dt.replace(hour=9),
                "stop": self.now_dt.replace(hour=9) + relativedelta(hours=1),
                "of_state": "draft",
                "of_order_id": order.id,
            }
        )
        self.assertFalse(order.of_reference_laying_date)
        self.assertEqual(order.of_laying_week, "Non programmée")

        # Create draft installation intervention - laying date should be set to the start date of the intervention
        self.env["calendar.event"].create(
            {
                "name": "Test Event",
                "of_type": "intervention",
                "of_company_id": self.company_fr.id,
                "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                "of_partner_id": self.customer_a.id,
                "of_request_id": service_request.id,
                "of_type_id": self.request_type_installation.id,
                "start": self.now_dt.replace(hour=10),
                "stop": self.now_dt.replace(hour=10) + relativedelta(hours=1),
                "of_state": "draft",
                "of_order_id": order.id,
            }
        )
        self.assertEqual(order.of_reference_laying_date, fields.Date.from_string("2025-01-15"))
        self.assertEqual(order.of_laying_week, "2025 - S03")

        # Create earlier confirmed intervention - laying date should be updated with the new date because it is earlier
        one_week_earlier = self.now_dt - relativedelta(weeks=1)  # 2025-01-08 07:00:00
        self.env["calendar.event"].create(
            {
                "name": "Test Event",
                "of_type": "intervention",
                "of_company_id": self.company_fr.id,
                "of_employee_ids": [Command.set([self.employee_tech_johnny.id])],
                "of_partner_id": self.customer_a.id,
                "of_request_id": service_request.id,
                "of_type_id": self.request_type_installation.id,
                "start": one_week_earlier.replace(hour=14),
                "stop": one_week_earlier.replace(hour=14) + relativedelta(hours=1),
                "of_state": "confirmed",
                "of_order_id": order.id,
            }
        )
        self.assertEqual(order.of_reference_laying_date, fields.Date.from_string("2025-01-08"))
        self.assertEqual(order.of_laying_week, "2025 - S02")

        # Force manual laying date - laying date should be updated with the manual date
        order.write({"of_force_laying_date": True, "of_manual_laying_date": fields.Date.from_string("2025-02-01")})
        self.assertEqual(order.of_reference_laying_date, fields.Date.from_string("2025-02-01"))
        self.assertEqual(order.of_laying_week, "2025 - S05")

        # Disable force laying date - laying date should be updated with the earliest confirmed intervention
        order.write({"of_force_laying_date": False})
        self.assertEqual(order.of_reference_laying_date, fields.Date.from_string("2025-01-08"))
        self.assertEqual(order.of_laying_week, "2025 - S02")

        # Cancel confirmed intervention - laying date should be updated with the next earliest confirmed intervention
        order.of_intervention_ids.filtered(lambda ev: ev.of_state == "confirmed").action_button_cancel()
        self.assertEqual(order.of_reference_laying_date, fields.Date.from_string("2025-01-15"))
        self.assertEqual(order.of_laying_week, "2025 - S03")
