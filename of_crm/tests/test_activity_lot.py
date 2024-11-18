# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestMailActivityLot(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

        self.user_crm = self.env["res.users"].create(
            {
                "name": "user_crm",
                "login": "user_crm",
                "email": "user_crm@openfire.fr",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("sales_team.group_sale_salesman_all_leads").id,
                        ]
                    )
                ],
                "company_id": self.company_fr.id,
            }
        )

        self.ActivityType = self.env["mail.activity.type"]

        self.activity1, self.activity2, self.activity3, self.activity4, self.activity5 = self.ActivityType.create(
            [
                {
                    "name": "Activity 1",
                    "delay_count": 2,
                    "delay_unit": "days",
                    "delay_from": "previous_activity",
                    "category": "default",
                    "default_user_id": self.user_accountant.id,
                },
                {
                    "name": "Activity 2",
                    "delay_count": 1,
                    "delay_unit": "days",
                    "delay_from": "previous_activity",
                    "category": "default",
                    "default_user_id": self.user_crm.id,
                },
                {
                    "name": "Activity 3",
                    "delay_count": 5,
                    "delay_unit": "days",
                    "delay_from": "previous_activity",
                    "category": "default",
                    "default_user_id": self.user_crm.id,
                },
                {
                    "name": "Activity 4",
                    "delay_count": 1,
                    "delay_unit": "weeks",
                    "delay_from": "previous_activity",
                    "category": "default",
                    "default_user_id": self.user_crm.id,
                },
                {
                    "name": "Activity 5",
                    "delay_count": 1,
                    "delay_unit": "months",
                    "delay_from": "previous_activity",
                    "category": "default",
                    "default_user_id": self.user_crm.id,
                },
            ]
        )

        self.activity_lot_type = self.ActivityType.create(
            {
                "name": "Lot of Activities",
                "category": "activities_lot",
                "of_activities_type": [
                    Command.set(
                        (self.activity1 + self.activity2 + self.activity3 + self.activity4 + self.activity5).ids
                    )
                ],
            }
        )

        self.opportunity = self.env["crm.lead"].create(
            {"name": "Test activities", "partner_id": self.env["res.partner"].create({"name": "Test activities"}).id}
        )

    @freeze_time("2024-12-18")
    @patch("odoo.addons.mail.models.mail_followers.Followers._insert_followers")
    def test_01_create_activities_from_lot(self, mock__insert_followers):
        """Tests the generation of activities from an activity batch.

        The date calculation should be as follows:
            Base date : 18/12/2024
            Activity 1 : +2 days => 20/12/2024
            Activity 2 : +1 days from previous => 21/12/2024
            Activity 3 : +5 days from previous => 26/12/2024
            Activity 4 : +1 week from previous => 02/01/2025 (26/12 + 7 days)
            Activity 5 : +1 month from previous => 02/02/2025
        """
        # Mock `_insert_followers` methods to avoid UniqueViolation error in this test.
        # We just want to test the multiple creation of activities and their deadline dates.
        mock__insert_followers.return_value = self.env["mail.followers"]

        self.env["mail.activity"].create(
            {
                "res_id": self.opportunity.id,
                "res_model_id": self.env.ref("crm.model_crm_lead").id,
                "activity_type_id": self.activity_lot_type.id,
            }
        )

        # Check that we have our 5 activities
        activities = self.env["mail.activity"].search([("res_id", "=", self.opportunity.id)], order="id asc")
        self.assertEqual(len(activities), 5, "Should have created 5 activities for the lot")

        # Check data
        self.assertRecordValues(
            activities,
            [
                {"date_deadline": date(2024, 12, 20), "user_id": self.user_accountant.id},
                {"date_deadline": date(2024, 12, 21), "user_id": self.user_crm.id},
                {"date_deadline": date(2024, 12, 26), "user_id": self.user_crm.id},
                {"date_deadline": date(2025, 1, 2), "user_id": self.user_crm.id},
                {"date_deadline": date(2025, 2, 2), "user_id": self.user_crm.id},
            ],
        )
