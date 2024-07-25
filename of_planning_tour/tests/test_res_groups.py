# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_planning_tour.tests.common import TestOFPlanningTourCommon


class TestResGroups(TestOFPlanningTourCommon):
    def test_01_check_tours_groups(self):
        """Checks that the user cannot be in both groups at the same time."""

        test_user = self.env['res.users'].create(
            {
                'name': 'Test User',
                'login': 'test_user',
            }
        )
        self.assertTrue(self.group_tour_no_manual_creation in test_user.groups_id)

        # Add the user to the manual creation group
        self.group_tour_manual_creation.users = [Command.link(test_user.id)]

        # Check that the user is in the manual creation group and not in the no manual creation group
        self.assertTrue(self.group_tour_manual_creation in test_user.groups_id)
        self.assertFalse(self.group_tour_no_manual_creation in test_user.groups_id)

        # Add the user to the no manual creation group
        self.group_tour_no_manual_creation.users = [Command.link(test_user.id)]

        # Check that the user is in the no manual creation group and not in the manual creation group anymore
        self.assertTrue(self.group_tour_no_manual_creation in test_user.groups_id)
        self.assertFalse(self.group_tour_manual_creation in test_user.groups_id)
