# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_planning_tour.tests.common import TestOFPlanningTourCommon


class TestResUsers(TestOFPlanningTourCommon):
    def setUp(self):
        super().setUp()
        self.test_user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
            }
        )

    def test_01_create_user(self):
        """Check that when a user is created, he is added in the "no manual creation group" (default group)."""
        self.assertTrue(self.group_tour_no_manual_creation in self.test_user.groups_id)

    def test_02_write_remove_default_group(self):
        """
        Check that when the default group is removed from the user, the user is added back to it.
        """
        self.test_user.groups_id = [  # Ensure the user is in the default group
            Command.set([self.group_tour_no_manual_creation.id])
        ]
        self.test_user.write({"groups_id": [Command.unlink(self.group_tour_no_manual_creation.id)]})
        self.assertTrue(self.group_tour_no_manual_creation in self.test_user.groups_id)

    def test_03_write_add_group_manual_creation(self):
        """Check that when the "manual creation group" is added to the user, the user is removed from the
        default group."""
        self.test_user.groups_id = [Command.set([self.group_tour_no_manual_creation.id])]
        self.test_user.write({"groups_id": [Command.link(self.group_tour_manual_creation.id)]})
        self.assertTrue(self.group_tour_manual_creation in self.test_user.groups_id)
        self.assertFalse(self.group_tour_no_manual_creation in self.test_user.groups_id)

    def test_04_write_add_group_no_manual_creation(self):
        """Check that when the "no manual creation group" is added to the user, the user is removed from the
        "manual creation group"."""
        self.test_user.groups_id = [Command.set([self.group_tour_manual_creation.id])]
        self.test_user.write({"groups_id": [Command.link(self.group_tour_manual_creation.id)]})
        self.assertTrue(self.group_tour_manual_creation in self.test_user.groups_id)
        self.assertFalse(self.group_tour_no_manual_creation in self.test_user.groups_id)

    def test_05_write_add_both_groups(self):
        """Check that when both groups are added to the user, the user is removed from the default group."""
        self.test_user.write(
            {"groups_id": [Command.set([self.group_tour_manual_creation.id, self.group_tour_no_manual_creation.id])]}
        )
        self.assertTrue(self.group_tour_manual_creation in self.test_user.groups_id)
        self.assertFalse(self.group_tour_no_manual_creation in self.test_user.groups_id)

    def test_06_write_remove_both_groups(self):
        """Check that when both groups are removed from the user, the user is added back to the default group."""
        self.test_user.with_context(of_avoid_check_tours_groups=True).write(
            {
                "groups_id": [
                    Command.set([self.group_tour_manual_creation.id, self.group_tour_no_manual_creation.id]),
                ]
            }
        )
        self.test_user.write(
            {
                "groups_id": [
                    Command.unlink(self.group_tour_manual_creation.id),
                    Command.unlink(self.group_tour_no_manual_creation.id),
                ]
            }
        )
        self.assertTrue(self.group_tour_no_manual_creation in self.test_user.groups_id)
        self.assertFalse(self.group_tour_manual_creation in self.test_user.groups_id)
