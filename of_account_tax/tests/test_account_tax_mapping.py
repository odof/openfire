# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFAccountTaxMapping(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create user
        cls.user_accountant = cls.env['res.users'].create(
            {
                'name': 'user_accountant',
                'login': 'user_accountant',
                'email': 'user_accountant@openfire.fr',
                'groups_id': [(6, 0, [cls.env.ref('account.group_account_manager').id])],
                'company_id': cls.company_fr.id,
            }
        )

        # Create accounts
        cls.account_707022 = cls.env['account.account'].create(
            {
                'name': 'Test Account 5.5%',
                'code': '707022',
                'account_type': 'income',
                'company_id': cls.company_fr.id,
            }
        )
        cls.account_707027 = cls.env['account.account'].create(
            {
                'name': 'Test Account 20.0%',
                'code': '707027',
                'account_type': 'income',
                'company_id': cls.company_fr.id,
            }
        )

        # Create category and product
        cls.category_id = cls.env['product.category'].create(
            {
                'name': 'Test Category 5.5%',
                'property_account_income_categ_id': cls.account_707022.id,
            }
        )
        cls.product_test_mapping = cls.env['product.product'].create(
            {
                'name': 'Test Product Mapping',
                'categ_id': cls.category_id.id,
                'taxes_id': [Command.set([cls.tax_base.id])],
            }
        )

        # Update taxes with account mapping
        cls.tax_5_5.write(
            {
                'of_account_ids': [
                    Command.create(
                        {
                            'account_src_id': cls.account_707027.id,
                            'account_dest_id': cls.account_707022.id,
                        }
                    )
                ]
            }
        )

        cls.tax_20.write(
            {
                'of_account_ids': [
                    Command.create(
                        {
                            'account_src_id': cls.account_707022.id,
                            'account_dest_id': cls.account_707027.id,
                        }
                    )
                ]
            }
        )

    def test_01_account_move_tax_mapping(self):
        """Test account move tax mapping on invoice line.

        By switching taxes on invoice line, account mapping should be applied and account should be changed by
        the account mapping defined on the tax.
        """
        with Form(
            self.env['account.move']
            .with_context(default_move_type='out_invoice')
            .with_context(default_company_id=self.company_fr.id)
        ) as move_form:
            move_form.partner_id = self.customer_a
            move_form.fiscal_position_id = self.fiscal_pos_20
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_test_mapping
                line_form.quantity = 1
                line_form.price_unit = 100
        move = move_form.save()

        # Check taxes, at this point, fiscal position should be applied and base tax should be switched with the tax
        # 20.0%. Also account mapping should be applied too and the account "707027 Test Account 20.0%"" should be used
        self.assertRecordValues(
            move.invoice_line_ids,
            [
                {'tax_ids': [self.tax_20.id], 'account_id': self.account_707027.id},
            ],
        )

        # Change the tax to 5.5% and check that the account mapping is applied
        with Form(move) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.tax_ids.clear()
                line_form.tax_ids.add(self.tax_5_5)
        move = move_form.save()

        # Account mapping should be applied and the account "707022 Test Account 5.5%" should be used now
        self.assertRecordValues(
            move.invoice_line_ids,
            [
                {'tax_ids': [self.tax_5_5.id], 'account_id': self.account_707022.id},
            ],
        )

    def test_02_account_move_tax_mapping_with_fiscal_position(self):
        """Test the update of fiscal position on invoice.

        By switching fiscal position on invoice, tax should be recomputed on invoice line and account mapping should
        be applied with the new tax.
        """
        with Form(
            self.env['account.move']
            .with_context(default_move_type='out_invoice')
            .with_context(default_company_id=self.company_fr.id)
        ) as move_form:
            move_form.partner_id = self.customer_a
            move_form.fiscal_position_id = self.fiscal_pos_20
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_test_mapping
                line_form.quantity = 1
                line_form.price_unit = 100
        move = move_form.save()

        # Check taxes, at this point, fiscal position should be applied and base tax should be switched with the tax
        # 20.0%. Also account mapping should be applied too and account "707027 Test Account 20.0%" should be used now
        self.assertRecordValues(
            move.invoice_line_ids,
            [
                {'tax_ids': [self.tax_20.id], 'account_id': self.account_707027.id},
            ],
        )

        # Change the fiscal position to 5.5% and check that the account mapping is applied
        with Form(move) as move_form:
            move_form.fiscal_position_id = self.fiscal_pos_5_5
        move = move_form.save()

        # Account mapping should be applied and the account 707022 Test Account 5.5% should be used
        self.assertRecordValues(
            move.invoice_line_ids,
            [
                {'tax_ids': [self.tax_5_5.id], 'account_id': self.account_707022.id},
            ],
        )
