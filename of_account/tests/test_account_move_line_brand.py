# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFAccountMoveLineBrand(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_brand_use_desc = cls.env['of.product.brand'].create(
            {
                'name': "Test Brand Use Description",
                'code': "TBUD",
                'use_brand_description_sale': True,
                'description_sale': "Brand Description\nProduct : {{object.name}}",
                'show_in_sales': True,
                'partner_id': cls.supplier_a.id,
            }
        )
        cls.product_brand_dont_use_desc = cls.env['of.product.brand'].create(
            {
                'name': "Test Brand No Description",
                'code': "TBNUD",
                'use_brand_description_sale': False,
                'description_sale': "Brand Description\nProduct : {{object.name}}",
                'show_in_sales': True,
                'partner_id': cls.supplier_a.id,
            }
        )

    def test_01_of_product_brand_id(self):
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_use_desc.id,
            }
        )

        with Form(
            self.env['account.move']
            .with_user(self.user_accountant)
            .with_context(default_move_type='out_invoice', default_journal_id=self.journal_sale.id)
        ) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product

        move = move_form.save()
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertEqual(move.invoice_line_ids[0].of_product_brand_id, product.brand_id)

    def test_02_compute_name_use_description(self):
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_use_desc.id,
            }
        )

        with Form(
            self.env['account.move']
            .with_user(self.user_accountant)
            .with_context(default_move_type='out_invoice', default_journal_id=self.journal_sale.id)
        ) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                self.assertEqual(
                    line_form.name,
                    'Test Brand Use Description - Test Product Use Desc\nBrand Description\n'
                    'Product : Test Product Use Desc',
                )

    def test_03_compute_name_no_use_description(self):
        product = self.create_product(
            {
                'name': 'Test Product Use Desc',
                'brand_id': self.product_brand_dont_use_desc.id,
            }
        )

        with Form(
            self.env['account.move']
            .with_user(self.user_accountant)
            .with_context(default_move_type='out_invoice', default_journal_id=self.journal_sale.id)
        ) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                self.assertEqual(line_form.name, 'Test Brand No Description - Test Product Use Desc')
