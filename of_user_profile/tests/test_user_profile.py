# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

logger = logging.getLogger(__name__)


@tagged("openfire_custom")
class TestOFUserProfile(TransactionCase):
    def setUp(self):
        super().setUp()

        self.res_group1 = self.env["res.groups"].create({"name": "Group 1"})
        self.res_group2 = self.env["res.groups"].create({"name": "Group 2"})

    def test_01_user_profile_groups(self):
        """Test that a user with a specific profile has the right groups assigned."""
        profile_user = self.env["res.users"].create(
            {
                "name": "Profile User",
                "login": "profile_user",
                "password": "password",
                "email": "profile_user@test.example.com",
                "of_is_user_profile": True,
                "groups_id": [
                    Command.set([self.env.ref("base.group_user").id, self.res_group1.id, self.res_group2.id])
                ],
            }
        )

        normal_user = self.env["res.users"].create(
            {
                "name": "Normal User",
                "login": "normal_user",
                "password": "password",
                "email": "normal_user@test.example.com",
                "of_user_profile_id": profile_user.id,
            }
        )

        self.assertIn(
            self.res_group1.id,
            normal_user.groups_id,
            "Normal user should inherit groups from profile user",
        )
        self.assertIn(
            self.res_group2.id,
            normal_user.groups_id,
            "Normal user should inherit groups from profile user",
        )

        self.assertEqual(profile_user.of_users_count, 1, "Profile user should have one user assigned")

    def test_02_profile_user_constraints(self):
        """Test constraints on profile users."""
        with self.assertRaises(ValidationError):
            self.env["res.users"].create(
                {
                    "name": "Admin Profile User",
                    "login": "admin_profile_user",
                    "email": "admin_profile_user@test.example.com",
                    "of_is_user_profile": True,
                    "of_user_profile_id": self.env.ref("base.user_admin").id,
                }
            )

    def test_03_onchange_of_is_user_profile(self):
        """Test the onchange behavior of of_is_user_profile field."""
        user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
                "email": "test_user@test.example.com",
                "notification_type": "email",
            }
        )
        user.of_is_user_profile = True
        user._onchange_of_is_user_profile()
        self.assertFalse(user.active, "User should be inactive when marked as profile")
        self.assertFalse(user.of_user_profile_id, "User profile ID should be reset when marked as profile")
