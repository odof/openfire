# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError, UserError

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFAccountAccount(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.account_payable_7071_tmpl = cls.env.ref("l10n_fr.pcg_7071")
        cls.account_receivable_4111_tmpl = cls.env.ref("l10n_fr.fr_pcg_recv")

        cls.account_payable = cls.env["account.account"].search(
            [("company_id", "=", cls.company_fr.id), ("code", "=", "707100")], limit=1
        )
        cls.account_receivable = cls.env["account.account"].search(
            [("company_id", "=", cls.company_fr.id), ("code", "=", "411100")], limit=1
        )

    def test_01_account_account_with_entry_lines(self):
        """Test the account is not editable if it has entry lines."""

        # There is no entry lines linked to this account yet, the user can change the code
        self.account_payable.with_user(self.user_accountant).write({"code": "707100TEST"})

        move_lines = {
            "line_ids": [
                (0, 0, {"name": "debit", "account_id": self.account_payable.id, "debit": 100.0, "credit": 0.0}),
                (0, 0, {"name": "credit", "account_id": self.account_receivable.id, "debit": 0.0, "credit": 100.0}),
            ],
        }
        self.env["account.move"].create(move_lines)

        # User accountant can't change the code of the account because it has entry lines and he is not in the special
        # group that allows him to do it.
        with self.assertRaises(UserError):
            self.account_payable.with_user(self.user_accountant).write({"code": "707100"})

        # User can change the code because he is in the special group
        self.user_accountant.write(
            {"groups_id": [(4, self.env.ref("of_account.of_account_can_modify_account_with_entry_lines").id)]}
        )
        self.account_payable.with_user(self.user_accountant).write({"code": "707100"})

    def test_02_account_account_of_editable_rule(self):
        """Test the account is not editable if the field `of_editable` is False."""

        # There is no entry lines linked to this account yet, the user can change the code
        self.account_payable.with_user(self.user_accountant).write({"code": "707100TEST"})

        # User can't change the code because the field `of_editable` is False
        self.account_payable.write({"of_editable": False})
        with self.assertRaises(AccessError):
            self.account_payable.with_user(self.user_accountant).write({"code": "707100"})

        # User can change the code because the field `of_editable` is True
        self.account_payable.write({"of_editable": True})
        self.account_payable.with_user(self.user_accountant).write({"code": "707100"})
