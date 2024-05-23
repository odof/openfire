# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.of_base.tests.common import TestOFBaseCommon


class TestOFBaseResGroups(TestOFBaseCommon):
    def test_01_check_admin_only_group_create(self):
        """
        Test case to check if a UserError is raised when trying to create a user
        with a group that can only be assigned to the admin account.
        """
        with self.assertRaises(UserError) as create_user_error:
            self.env['res.users'].create(
                {
                    'name': 'Test User',
                    'login': 'test_user',
                    'password': 'password',
                    'groups_id': [Command.set([self.env.ref('of_base.of_group_root_only').id])],
                }
            )
        self.assertEqual(
            "Only the admin account can belong to group \"Admin only\".", create_user_error.exception.args[0]
        )

    def test_02_check_admin_only_group_write(self):
        """
        Test case to check if a non-admin user can write to the 'Admin only' group.
        """
        user = self.env['res.users'].create(
            {
                'name': 'Test User',
                'login': 'test_user',
                'password': 'password',
            }
        )

        group_root = self.env.ref('of_base.of_group_root_only').sudo()

        with self.assertRaises(UserError) as write_user_error:
            user.write({'groups_id': [Command.link(group_root.id)]})
        self.assertEqual(
            "Only the admin account can belong to group \"Admin only\".", write_user_error.exception.args[0]
        )
