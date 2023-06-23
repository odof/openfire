# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFAccountMoveLine(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_accountant = cls.env['res.users'].create(
            {
                'name': 'user_accountant',
                'login': 'user_accountant',
                'email': 'user_accountant@openfire.fr',
                # Theses groups are required to create a new account.move to avoid the error:
                #  AssertionError: line_ids was not found in the view
                'groups_id': [
                    (6, 0, cls.env.user.groups_id.ids),
                    (4, cls.env.ref('account.group_account_manager').id),
                    (4, cls.env.ref('account.group_account_user').id),
                ],
                'company_id': cls.company_fr.id,
            }
        )

        # Journals
        cls.journal_purchase = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company_fr.id)], limit=1
        )
        cls.journal_sale = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company_fr.id)], limit=1
        )
        cls.journal_bank = cls.env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', cls.company_fr.id)], limit=1
        )

        # Accounts
        cls.account_customer_a_recivable = cls.env['account.account'].create(
            {
                'name': 'Customer A Recivable',
                'code': '411CUSTOMERA',
                'account_type': 'asset_receivable',
                'company_id': cls.company_fr.id,
            }
        )
        cls.account_supplier_a_payable = cls.env['account.account'].create(
            {
                'name': 'Supplier A Payable',
                'code': '401SUPPLIERA',
                'account_type': 'liability_payable',
                'company_id': cls.company_fr.id,
            }
        )
        cls.customer_a.property_account_receivable_id = cls.account_customer_a_recivable
        cls.supplier_a.property_account_payable_id = cls.account_supplier_a_payable

    def test_01_test_compute_account_id_purchase_journal(self):
        """Test that the account_id on the line is correctly computed when the journal is a purchase journal and the
        partner is a supplier. Account should be the payable account of the partner.
        """

        move = (
            self.env['account.move']
            .with_user(self.user_accountant)
            .create(
                {
                    'move_type': 'entry',
                    'journal_id': self.journal_purchase.id,
                }
            )
        )
        move.with_context(line_ids=move.line_ids).line_ids.create(
            [
                {
                    'move_id': move.id,
                    'partner_id': self.supplier_a.id,
                    'debit': 150,
                },
                {
                    'move_id': move.id,
                    'partner_id': self.supplier_a.id,
                    'credit': 150,
                },
            ]
        )
        self.assertEqual(move.line_ids[0].account_id, self.supplier_a.property_account_payable_id)

    def test_02_test_compute_account_id_bank_journal_and_supplier(self):
        """Test that the account_id on the line is correctly computed when the journal is a bank journal and the
        partner is a supplier. Account should be the payable account of the partner.
        """
        move = (
            self.env['account.move']
            .with_user(self.user_accountant)
            .create(
                {
                    'move_type': 'entry',
                    'journal_id': self.journal_bank.id,
                }
            )
        )
        move.with_context(line_ids=move.line_ids).line_ids.create(
            [
                {
                    'move_id': move.id,
                    'partner_id': self.supplier_a.id,
                    'debit': 150,
                },
                {
                    'move_id': move.id,
                    'partner_id': self.supplier_a.id,
                    'credit': 150,
                },
            ]
        )
        self.assertEqual(move.line_ids[0].account_id, self.supplier_a.property_account_payable_id)

    def test_03_test_compute_account_id_bank_journal_and_customer(self):
        """Test that the account_id on the line is correctly computed when the journal is a bank journal and the
        partner is a customer. Account should be the receivable account of the partner.
        """
        move = (
            self.env['account.move']
            .with_user(self.user_accountant)
            .create(
                {
                    'move_type': 'entry',
                    'journal_id': self.journal_bank.id,
                }
            )
        )
        move.with_context(line_ids=move.line_ids).line_ids.create(
            [
                {
                    'move_id': move.id,
                    'partner_id': self.customer_a.id,
                    'debit': 150,
                },
                {
                    'move_id': move.id,
                    'partner_id': self.customer_a.id,
                    'credit': 150,
                },
            ]
        )
        self.assertEqual(move.line_ids[0].account_id, self.customer_a.property_account_receivable_id)
