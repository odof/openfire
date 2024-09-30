# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFAccountJournal(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # FIXME: Add specific access rights to ir.sequence to avoid odoo.exceptions.AccessError when creating a new
        #  journal
        cls.env["ir.model.access"].create(
            {
                "name": "ir.sequence access",
                "model_id": cls.env.ref("base.model_ir_sequence").id,
                "group_id": cls.env.ref("account.group_account_manager").id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }
        )

        # Accounts
        cls.account_707100 = cls.env["account.account"].search(
            [("code", "=", "707100"), ("company_id", "=", cls.company_fr.id)], limit=1
        )
        cls.account_607100 = cls.env["account.account"].search(
            [("code", "=", "607100"), ("company_id", "=", cls.company_fr.id)], limit=1
        )

    def test_01_account_journal_restrict_mode_hash_table_value_admin(self):
        """Test the value of `restrict_mode_hash_table` field on account.journal depending on the type of the journal.
        A journal of type sale, bank, cash should have the value True.
        A journal of type purchase, general should have the value False.

        The user is admin, he can change the mode of a journal of type sale.
        """
        # Create a journal
        journal_obj = self.env["account.journal"]
        journal = journal_obj.create(
            {
                "name": "Test journal",
                "code": "TEST",
                "type": "sale",
                "company_id": self.company_fr.id,
            }
        )
        self.assertEqual(journal.restrict_mode_hash_table, True, "The hash table value should be True for type sale")

        # Change the mode, its ok because the user is admin
        journal.write({"restrict_mode_hash_table": False})

    def test_02_account_journal_restrict_mode_hash_table_value(self):
        """Test the value of `restrict_mode_hash_table` field on account.journal depending on the type of the journal.
        A journal of type sale, bank, cash should have the value True.
        A journal of type purchase, general should have the value False.
        """
        # Create a journal
        journal_obj = self.env["account.journal"]
        journal = journal_obj.with_user(self.user_accountant).create(
            {
                "name": "Test journal",
                "code": "TEST",
                "type": "sale",
                "company_id": self.company_fr.id,
            }
        )
        self.assertEqual(journal.restrict_mode_hash_table, True, "The hash table value should be True for type sale")

        # Change the mode, that should failed because the type is sale and a non admin user cannot change the mode
        # of a journal of type sale
        with self.assertRaises(UserError):
            journal.with_user(self.user_accountant).write({"restrict_mode_hash_table": False})

        # Change the type, the mode should be changed to False
        journal.with_user(self.user_accountant).write({"type": "purchase"})
        self.assertEqual(
            journal.restrict_mode_hash_table, False, "The hash table value should be False for type purchase"
        )

        # Change the mode, its ok because the type is purchase and a non admin user can change the mode for this type
        journal.with_user(self.user_accountant).write({"restrict_mode_hash_table": True})

    def test_03_cron_activate_restrict_mode_hash_table_on_journals(self):
        """Test the cron remove_update_posted_from_journals."""
        journal_obj = self.env["account.journal"]
        journal_sale, journal_purchase, journal_bank = journal_obj.create(
            [
                {
                    "name": "Test journal sale",
                    "code": "TJS",
                    "type": "sale",
                    "company_id": self.company_fr.id,
                    "default_account_id": self.account_707100.id,
                    "restrict_mode_hash_table": False,
                },
                {
                    "name": "Test journal purchase",
                    "code": "TJP",
                    "type": "purchase",
                    "company_id": self.company_fr.id,
                    "default_account_id": self.account_607100.id,
                    "restrict_mode_hash_table": False,
                },
                {
                    "name": "Test journal bank",
                    "code": "TJB",
                    "type": "bank",
                    "company_id": self.company_fr.id,
                    "restrict_mode_hash_table": False,
                },
            ]
        )

        cron = self.env.ref("of_account.account_journal_activate_restrict_mode_hash_table_on_journals")
        cron.write({"code": "model.cron_activate_restrict_mode_hash_table_on_journals(journal_types=['sale',])"})
        cron.method_direct_trigger()

        # Check the value of the field restrict_mode_hash_table, only the type sale should have the value changed to
        # True after the cron execution (by default)
        self.assertEqual(journal_sale.restrict_mode_hash_table, True)
        self.assertEqual(journal_purchase.restrict_mode_hash_table, False)
        self.assertEqual(journal_bank.restrict_mode_hash_table, False)

        # Reset the value of the field restrict_mode_hash_table to False for the sale journal
        journal_sale.write({"restrict_mode_hash_table": False})

        cron.write(
            {"code": "model.cron_activate_restrict_mode_hash_table_on_journals(journal_types=['sale', 'bank',])"}
        )
        cron.method_direct_trigger()

        # Check the value of the field restrict_mode_hash_table, only the type purchase should have the value
        # changed to True after the cron execution (by default)
        self.assertEqual(journal_sale.restrict_mode_hash_table, True)
        self.assertEqual(journal_purchase.restrict_mode_hash_table, False)
        self.assertEqual(journal_bank.restrict_mode_hash_table, True)

    def test_04_restrict_mode_hash_table_visibility(self):
        """Test the visibility of the field restrict_mode_hash_table depending on the type of the journal and the user

        Admin user can see the field `restrict_mode_hash_table` on a journal of type sale
        Non admin user cannot see the field `restrict_mode_hash_table` on a journal of type sale
        """
        journal_obj = self.env["account.journal"]
        journal = journal_obj.create(
            {
                "name": "Test sale journal 1",
                "code": "TSJ1",
                "type": "sale",
                "company_id": self.company_fr.id,
                "default_account_id": self.account_707100.id,
            }
        )
        with Form(journal) as journal_form:
            journal_form.restrict_mode_hash_table = True

        journal = journal_obj.with_user(self.user_accountant).create(
            {
                "name": "Test sale journal 2",
                "code": "TSJ2",
                "type": "sale",
                "company_id": self.company_fr.id,
                "default_account_id": self.account_707100.id,
            }
        )
        with Form(journal) as journal_form:
            with self.assertRaises(AssertionError):
                journal_form.restrict_mode_hash_table = True

        journal = journal_obj.with_user(self.user_accountant).create(
            {
                "name": "Test general journal",
                "code": "TGJ",
                "type": "general",
                "company_id": self.company_fr.id,
            }
        )
        with Form(journal) as journal_form:
            journal_form.restrict_mode_hash_table = True
