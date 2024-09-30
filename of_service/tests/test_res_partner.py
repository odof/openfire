# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.addons.of_service.tests.common import TestOFServiceCommon


class TestResPartner(TestOFServiceCommon):
    def test_01_compute_requests(self):
        """Test the _compute_requests method of res.partner

        Create 6 requests for the partner.

        4 of them should be computed in the request_to_schedule_ids, because they are not done or cancelled.
        1 of them should be computed in the recurring_request_ids, because it is a recurring request.

        The last one should not be computed in any of the two fields, because it is done.
        """
        today = fields.Date.today()
        in_15_days = today + relativedelta(days=15)
        three_days_ago = today - relativedelta(days=3)

        request_base_values = {
            "name": "Test Request",
            "partner_id": self.partner_tony.id,
            "state": "draft",
            "type_id": self.env.ref("of_service.of_service_request_type_installation").id,
            "task_id": self.task_installation.id,
            "company_id": self.company_fr.id,
            "next_date": today,
            "end_date": in_15_days,
        }
        request_1 = self.env["of.service.request"].create(request_base_values)

        request_values = request_base_values | {
            "name": "Test Request 2",
            "state": "to_plan",
            "base_state": "calculated",
        }
        request_2 = self.env["of.service.request"].create(request_values)

        request_values = request_base_values | {
            "name": "Test Request 3",
            "state": "part_planned",
            "base_state": "calculated",
        }
        request_3 = self.env["of.service.request"].create(request_values)

        request_values = request_base_values | {"name": "Test Request 4", "state": "late"}
        request_4 = self.env["of.service.request"].create(request_values)

        request_values = request_base_values | {
            "name": "Test Request 5",
            "state": "done",
            "recurrency": True,
            "remaining_duration": 0,
            "last_next_date": three_days_ago,
            "contract_end_date": three_days_ago,
            "base_state": "calculated",
        }
        self.env["of.service.request"].create(request_values)

        request_values = request_base_values | {
            "name": "Test Request 6",
            "state": "done",
            "recurrency": True,
            "remaining_duration": 0,
            "last_next_date": three_days_ago,
            "base_state": "calculated",
        }
        request_6 = self.env["of.service.request"].create(request_values)

        # Compute the requests for the partner
        self.partner_tony._compute_requests()

        # Check the computed values
        self.assertEqual(self.partner_tony.request_to_schedule_count, 4)
        self.assertEqual(self.partner_tony.recurring_request_count, 1)
        self.assertItemsEqual(self.partner_tony.request_to_schedule_ids, [request_1, request_2, request_3, request_4])
        self.assertItemsEqual(self.partner_tony.recurring_request_ids, [request_6])
