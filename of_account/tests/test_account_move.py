# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFAccountMove(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_accountant_2 = cls.env['res.users'].create(
            {
                'name': 'user_accountant_2',
                'login': 'user_accountant_2',
                'email': 'user_accountant_2@openfire.fr',
                # Theses groups are required to create a new account.move to avoid the error:
                #  AssertionError: line_ids was not found in the view
                "groups_id": [
                    (4, cls.env.ref("account.group_account_manager").id),
                    (4, cls.env.ref("account.group_account_user").id),
                ],
                'company_id': cls.company_fr.id,
            }
        )

        cls.journal_purchase = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company_fr.id)], limit=1
        )
        cls.account_607100 = cls.env['account.account'].search(
            [('code', '=', '607100'), ('company_id', '=', cls.company_fr.id)], limit=1
        )
        cls.account_401100 = cls.env['account.account'].search(
            [('code', '=', '401100'), ('company_id', '=', cls.company_fr.id)], limit=1
        )
        cls.account_607100.write({'of_account_counterpart_id': cls.account_401100.id})

    def test_01_entry_move_default_values_move_lines(self):
        """Test that the default values of move lines are correct when creating a new Entry move from scratch with the
        journal purchase.

        The second line should have the account 401100 as counterpart account.
        The second line should have the maturity date of the first line.
        """

        with Form(
            self.env['account.move']
            .with_user(self.user_accountant_2)
            .with_context(default_move_type='entry', default_journal_id=self.journal_purchase.id)
        ) as move_form:
            with move_form.line_ids.new() as line_form1:
                line_form1.account_id = self.account_607100
                line_form1.partner_id = self.customer_a
                line_form1.debit = 1500
                line_form1.date_maturity = fields.Date.today()

            with move_form.line_ids.new() as line_form2:
                line_form2.name = 'Test'

            self.assertEqual(line_form2.account_id, self.account_401100)
            self.assertEqual(line_form2.credit, 1500)
            self.assertEqual(line_form2.debit, 0)
            self.assertEqual(line_form2.date_maturity, fields.Date.today())

    def test_02_move_entry_commercial_partner_id_compute(self):
        """Test that the commercial partner is correctly computed when creating a new Entry move from scratch without
        partner.
        """

        with Form(
            self.env['account.move']
            .with_user(self.user_accountant_2)
            .with_context(default_move_type='entry', default_journal_id=self.journal_purchase.id)
        ) as move_form:
            with move_form.line_ids.new() as line_form:
                line_form.account_id = self.account_607100
                line_form.partner_id = self.customer_a
                line_form.debit = 1500
                line_form.date_maturity = fields.Date.today()

            with move_form.line_ids.new() as line_form:
                line_form.name = 'Test'

            self.assertEqual(move_form.commercial_partner_id, self.customer_a.commercial_partner_id)

        move = move_form.save()
        self.assertEqual(move.commercial_partner_id, self.customer_a.commercial_partner_id)

    def test_03_account_move_suitable_journal_ids(self):
        """Test that the suitable journal ids are correctly computed when creating a new Entry move from scratch."""

        move1 = (
            self.env['account.move']
            .with_user(self.user_accountant_2)
            .with_context(default_move_type='entry')
            .create({})
        )
        self.assertIn(self.journal_purchase, move1.suitable_journal_ids)

        suitable_default_type_domain = self.env.ref('of_account.of_account_suitable_default_type_domain')
        suitable_default_type_domain.write({'value': 'general,bank'})

        move2 = (
            self.env['account.move']
            .with_user(self.user_accountant_2)
            .with_context(default_move_type='entry')
            .create({})
        )
        self.assertNotIn(self.journal_purchase, move2.suitable_journal_ids)
