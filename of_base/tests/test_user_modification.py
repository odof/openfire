# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import AccessError, UserError

from odoo.addons.of_base.tests.common import TestOFBaseCommon


class TestOFBaseUserModification(TestOFBaseCommon):
    def setUp(self):
        super().setUp()
        self.user_admin = self.env.ref("base.user_admin")
        self.user_odoobot = self.env.ref("base.user_root")

        self.new_user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
                "password": "password",
            }
        )

        self.new_user_access_admin = self.env["res.users"].create(
            {
                "name": "Test User Access Admin",
                "login": "test_user_access_admin",
                "password": "password",
                "groups_id": [Command.link(self.env.ref("base.group_erp_manager").id)],
            }
        )

        self.new_user_admin = self.env["res.users"].create(
            {
                "name": "Test User Admin",
                "login": "test_user_admin",
                "password": "password",
                "groups_id": [Command.link(self.env.ref("base.group_system").id)],
            }
        )

    def test_01_user_modification_admin_nok(self):
        """
        Test case to check if a UserError is raised when trying to modify the information of the administrator account
        with a non-administrator account.
        """

        # A normal user tries to modify the information of the administrator account
        with self.assertRaises(UserError) as write_user_error:
            self.user_admin.with_user(self.new_user).write({"name": "Admin modified"})
        self.assertEqual(
            "Seul le compte administrateur peut modifier les informations du compte administrateur.",
            write_user_error.exception.args[0],
        )

        # A user with access to the administrator group tries to modify the information of the administrator account
        with self.assertRaises(UserError) as write_user_error:
            self.user_admin.with_user(self.new_user_access_admin).write({"name": "Admin modified"})
        self.assertEqual(
            "Seul le compte administrateur peut modifier les informations du compte administrateur.",
            write_user_error.exception.args[0],
        )

        # A user with the administrator group tries to modify the information of the administrator account
        with self.assertRaises(UserError) as write_user_error:
            self.user_admin.with_user(self.new_user_admin).write({"name": "Admin modified"})
        self.assertEqual(
            "Seul le compte administrateur peut modifier les informations du compte administrateur.",
            write_user_error.exception.args[0],
        )

    def test_02_user_modification_admin_ok(self):
        """
        Test case to check if the information of the administrator account can be modified by the administrator account.
        """
        self.user_admin.with_user(self.user_admin).write({"name": "Admin modified"})
        self.assertEqual(self.user_admin.name, "Admin modified")

        self.user_admin.with_user(self.user_odoobot).write({"name": "Admin modified 2"})
        self.assertEqual(self.user_admin.name, "Admin modified 2")

    def test_03_user_modification_by_admin_ok(self):
        """
        Test case to check if the information of a user can be modified by the administrator account.
        """
        # The administrator account modifies the information of a user (normal user, admin access user, admin user)
        self.new_user.with_user(self.user_admin).write({"name": "Test User modified"})
        self.assertEqual(self.new_user.name, "Test User modified")
        self.new_user_access_admin.with_user(self.user_admin).write({"name": "Test User Access Admin modified"})
        self.assertEqual(self.new_user_access_admin.name, "Test User Access Admin modified")
        self.new_user_admin.with_user(self.user_admin).write({"name": "Test User Admin modified"})
        self.assertEqual(self.new_user_admin.name, "Test User Admin modified")

        # The system account modifies the information of a user (normal user, admin access user, admin user)
        self.new_user.with_user(self.user_odoobot).write({"name": "Test User modified"})
        self.assertEqual(self.new_user.name, "Test User modified")
        self.new_user_access_admin.with_user(self.user_odoobot).write({"name": "Test User Access Admin modified 2"})
        self.assertEqual(self.new_user_access_admin.name, "Test User Access Admin modified 2")
        self.new_user_admin.with_user(self.user_odoobot).write({"name": "Test User Admin modified 2"})
        self.assertEqual(self.new_user_admin.name, "Test User Admin modified 2")

    def test_04_user_modification_by_user_nok(self):
        """
        Test case to check if an AccessError is raised when trying to modify the information of an administrator account
        """
        # A normal user tries to modify Admin information
        with self.assertRaises(AccessError):
            self.new_user_admin.with_user(self.new_user).write({"name": "Test User modified 2"})

        # A normal user tries to modify Admin Access information
        with self.assertRaises(AccessError):
            self.new_user_access_admin.with_user(self.new_user).write({"name": "Test User Access Admin modified 2"})

        # A normal user tries to modify another normal user information
        new_user2 = self.env["res.users"].create(
            {
                "name": "Test User 2",
                "login": "test_user_2",
                "password": "password",
            }
        )
        with self.assertRaises(AccessError):
            new_user2.with_user(self.new_user).write({"name": "Test User 2 modified"})

    def test_05_user_modification_by_himself_ok(self):
        self.new_user.with_user(self.new_user).write({"name": "Test User modified"})
        self.assertEqual(self.new_user.name, "Test User modified")

        self.new_user_access_admin.with_user(self.new_user_access_admin).write(
            {"name": "Test User Access Admin modified"}
        )
        self.assertEqual(self.new_user_access_admin.name, "Test User Access Admin modified")

        self.new_user_admin.with_user(self.new_user_admin).write({"name": "Test User Admin modified"})
        self.assertEqual(self.new_user_admin.name, "Test User Admin modified")
