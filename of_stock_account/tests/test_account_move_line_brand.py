# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFAccountMoveLineBrand(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_of_product_brand_id(self):
        product = self.create_product(
            {
                "name": "Test Product Use Desc",
                "brand_id": self.product_brand_a.id,
            }
        )

        with Form(
            self.env["account.move"]
            .with_user(self.user_accountant)
            .with_context(default_move_type="out_invoice", default_journal_id=self.journal_sale.id)
        ) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product

        move = move_form.save()
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertEqual(move.invoice_line_ids[0].of_product_brand_id, product.brand_id)

    def test_02_compute_name_use_description(self):
        product = self.create_product(
            {
                "name": "Test Product Use Desc",
                "brand_id": self.product_brand_a.id,
            }
        )

        with Form(
            self.env["account.move"]
            .with_user(self.user_accountant)
            .with_context(default_move_type="out_invoice", default_journal_id=self.journal_sale.id)
        ) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                self.assertEqual(
                    line_form.name,
                    "Brand A - Test Product Use Desc\nBrand A Description\n" "Product : Test Product Use Desc",
                )

    def test_03_compute_name_no_use_description(self):
        product = self.create_product(
            {
                "name": "Test Product Use Desc",
                "brand_id": self.product_brand_b.id,
            }
        )

        with Form(
            self.env["account.move"]
            .with_user(self.user_accountant)
            .with_context(default_move_type="out_invoice", default_journal_id=self.journal_sale.id)
        ) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                self.assertEqual(line_form.name, "Brand B - Test Product Use Desc")
